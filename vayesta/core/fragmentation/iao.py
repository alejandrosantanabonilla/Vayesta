import numpy as np

import pyscf
import pyscf.lo

from vayesta.core.util import *
from .fragmentation import Fragmentation

class IAO_Fragmentation(Fragmentation):

    name = "IAO"

    def __init__(self, qemb, minao='minao'):
        super().__init__(qemb)
        self.minao = minao

    def get_refmol(self):
        refmol = pyscf.lo.iao.reference_mol(self.mol, minao=self.minao)
        return refmol

    def get_coeff(self, add_virtuals=True):
        """Make intrinsic atomic orbitals (IAOs).

        Returns
        -------
        c_iao : (n(AO), n(IAO)) array
            Orthonormalized IAO coefficients.
        """
        mo_coeff = self.mo_coeff
        ovlp = self.get_ovlp()

        c_occ = self.mo_coeff[:,self.mo_occ>0]
        c_iao = pyscf.lo.iao.iao(self.mol, c_occ, minao=self.minao)
        n_iao = c_iao.shape[-1]
        self.log.info("n(AO)= %4d  n(MO)= %4d  n(occ-MO)= %4d  n(IAO)= %4d",
                mo_coeff.shape[0], mo_coeff.shape[-1], c_occ.shape[-1], n_iao)

        # Orthogonalize IAO using symmetric (Lowdin) orthogonalization
        x, e_min = self.get_lowdin_orth_x(c_iao, ovlp)
        self.log.debug("Lowdin orthogonalization of IAOs: n(in)= %3d -> n(out)= %3d , e(min)= %.3e",
                x.shape[0], x.shape[1], e_min)
        if e_min < 1e-12:
            self.log.warning("Small eigenvalue in Lowdin-orthogonalization: %.3e !", e_min)
        c_iao = np.dot(c_iao, x)

        # Check that all electrons are in IAO space
        ne_iao = einsum('ai,ab,bc,cd,di->', c_iao, ovlp, self.mf.make_rdm1(), ovlp, c_iao)
        if abs(ne_iao - self.mol.nelectron) > 1e-8:
            self.log.error("IAOs do not contain the correct number of electrons: %.8f", ne_iao)
        else:
            self.log.debugv("Number of electrons in IAOs: %.8f", ne_iao)

        if add_virtuals:
            c_vir = self.get_virtual_coeff(c_iao)
            c_iao = np.hstack((c_iao, c_vir))
        # Test orthogonality of IAO
        self.check_orth(c_iao, "IAO")
        return c_iao

    def get_labels(self):
        """Get labels of IAOs.

        Returns
        -------
        iao_labels : list of length nIAO
            Orbital label (atom-id, atom symbol, nl string, m string) for each IAO.
        """
        refmol = self.get_refmol()
        iao_labels_refmol = refmol.ao_labels(None)
        self.log.debugv('iao_labels_refmol: %r', iao_labels_refmol)
        if refmol.natm == self.mol.natm:
            iao_labels = iao_labels_refmol
        # If there are ghost atoms in the system, they will be removed in refmol.
        # For this reason, the atom IDs of mol and refmol will not agree anymore.
        # Here we will correct the atom IDs of refmol to agree with mol
        # (they will no longer be contiguous integers).
        else:
            ref2mol = []
            for refatm in range(refmol.natm):
                ref_coords = refmol.atom_coord(refatm)
                for atm in range(self.mol.natm):
                    coords = self.mol.atom_coord(atm)
                    if np.allclose(coords, ref_coords):
                        self.log.debugv('reference cell atom %r maps to atom %r', refatm, atm)
                        ref2mol.append(atm)
                        break
                else:
                    raise RuntimeError("No atom found with coordinates %r" % ref_coords)
            iao_labels = []
            for iao in iao_labels_refmol:
                iao_labels.append((ref2mol[iao[0]], iao[1], iao[2], iao[3]))
        self.log.debugv('iao_labels: %r', iao_labels)
        assert (len(iao_labels_refmol) == len(iao_labels))
        return iao_labels

    def get_virtual_coeff(self, c_iao):

        mo_coeff = self.mo_coeff
        ovlp = self.get_ovlp()
        # Add remaining virtual space, work in MO space, so that we automatically get the
        # correct linear dependency treatment, if n(MO) < n(AO)
        c_iao_mo = dot(mo_coeff.T, ovlp, c_iao)
        # Get eigenvectors of projector into complement
        p_iao = np.dot(c_iao_mo, c_iao_mo.T)
        p_rest = np.eye(p_iao.shape[-1]) - p_iao
        e, c = np.linalg.eigh(p_rest)

        # Corresponding expression in AO basis (but no linear-dependency treatment):
        # p_rest = ovlp - ovlp.dot(c_iao).dot(c_iao.T).dot(ovlp)
        # e, c = scipy.linalg.eigh(p_rest, ovlp)
        # c_rest = c[:,e>0.5]

        # Ideally, all eigenvalues of P_env should be 0 (IAOs) or 1 (non-IAO)
        # Error if > 1e-3
        mask_iao, mask_rest = (e <= 0.5), (e > 0.5)
        e_iao, e_rest = e[mask_iao], e[mask_rest]
        if np.any(abs(e_iao) > 1e-3):
            self.log.error("CRITICAL: Some IAO eigenvalues of 1-P_IAO are not close to 0:\n%r", e_iao)
        elif np.any(abs(e_iao) > 1e-6):
            self.log.warning("Some IAO eigenvalues e of 1-P_IAO are not close to 0: n= %d max|e|= %.2e",
                    np.count_nonzero(abs(e_iao) > 1e-6), abs(e_iao).max())
        if np.any(abs(1-e_rest) > 1e-3):
            self.log.error("CRITICAL: Some non-IAO eigenvalues of 1-P_IAO are not close to 1:\n%r", e_rest)
        elif np.any(abs(1-e_rest) > 1e-6):
            self.log.warning("Some non-IAO eigenvalues e of 1-P_IAO are not close to 1: n= %d max|1-e|= %.2e",
                    np.count_nonzero(abs(1-e_rest) > 1e-6), abs(1-e_rest).max())

        if not (np.sum(mask_rest) + c_iao.shape[-1] == mo_coeff.shape[-1]):
            self.log.critical("Error in construction of remaining virtual orbitals! Eigenvalues of projector 1-P_IAO:\n%r", e)
            self.log.critical("Number of eigenvalues above 0.5 = %d", np.sum(mask_rest))
            self.log.critical("Total number of orbitals = %d", mo_coeff.shape[-1])
            raise RuntimeError("Incorrect number of remaining virtual orbitals")
        c_rest = np.dot(mo_coeff, c[:,mask_rest])        # Transform back to AO basis

        self.check_orth(np.hstack((c_iao, c_rest)), "IAO+virtual orbitals")
        return c_rest
