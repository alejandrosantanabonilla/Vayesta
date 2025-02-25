import functools
import logging

import vayesta
import vayesta.core
from vayesta.core.util import *


def scf_with_mpi(mpi, mf, mpi_rank=0, log=None):
    """Use to run SCF only on the master node and broadcast result afterwards."""

    if not mpi:
        return mf

    bcast = functools.partial(mpi.world.bcast, root=mpi_rank)
    kernel_orig = mf.kernel
    log = log or mpi.log or logging.getLogger(__name__)

    def mpi_kernel(self, *args, **kwargs):
        if mpi.rank == mpi_rank:
            log.info("MPI rank= %3d is running SCF", mpi.rank)
            with log_time(log.timing, "Time for SCF: %s"):
                res = kernel_orig(*args, **kwargs)
            log.info("MPI rank= %3d finished SCF", mpi.rank)
        else:
            res = None
            # Generate auxiliary cell, compensation basis etc,..., but not 3c integrals:
            if hasattr(self, 'with_df') and self.with_df.auxcell is None:
                self.with_df.build(with_j3c=False)
            log.info("MPI rank= %3d is waiting for SCF results", mpi.rank)
        mpi.world.barrier()

        # Broadcast results
        with log_time(log.timing, "Time for MPI broadcast of SCF results: %s"):
            res = bcast(res)
            if hasattr(self, 'with_df'):
                self.with_df._cderi = bcast(self.with_df._cderi)
            self.converged = bcast(self.converged)
            self.e_tot = bcast(self.e_tot)
            self.mo_energy = bcast(self.mo_energy)
            self.mo_occ = bcast(self.mo_occ)
            self.mo_coeff = bcast(self.mo_coeff)
        return res

    # TODO: Distribute diagonalization over k-points
    #def mpi_eig(self, h_kpts, s_kpts):
    #    nkpts = len(h_kpts)
    #    #mo_energy = []
    #    #mo_coeff = []

    #    # Broadcast hcore
    #    send = [[] for i in len(mpi)]
    #    for k in range(nkpts):
    #        send[k].append(h_kpts)
    #    h_list = mpi.world.scatter(send, root=mpi_rank)

    #    # Broadcast overlap
    #    send = [[] for i in len(mpi)]
    #    for k in range(nkpts):
    #        send[k].append(s_kpts)
    #    s_list = mpi.world.scatter(send, root=mpi_rank)

    #    # Diagonalize locally
    #    mo_energy_list, mo_coeff_list = eig_orig(h_list, s_list)

    #    # Gather results
    #    mo_energy = mpi.world.gather(mo_energy_list, root=mpi_rank)
    #    mo_coeff = mpi.world.gather(mo_coeff_list, root=mpi_rank)
    #    return mo_energy, mo_coeff

    mf.kernel = mpi_kernel.__get__(mf)
    mf.with_mpi = True

    return mf
