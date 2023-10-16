import zipfile
import json
import os
import tempfile
import matplotlib.pyplot as plt


def open_zip_files(folder_path):
  """Opens all zip files in the given folder.

  Args:
    folder_path: The path to the folder containing the zip files.

  Returns:
    A list of zip file objects.

  """

  zip_files = []
  for filename in os.listdir(folder_path):
    if filename.endswith(".zip"):
      zip_file = zipfile.ZipFile(os.path.join(folder_path, filename), "r")
      zip_files.append(zip_file)
  return zip_files

def remove_time_information(date_string):
  """Removes the time information from a date string in the 
     format 2022-10-03T00:00:00Z.

  Args:
    date_string: A string representing a date in the format 2022-10-03T00:00:00Z.

  Returns:
     A string representing the date without the time information, 
     in the format 2022-10-03.
  """
  import datetime
  
  date_time = datetime.datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%SZ")
  date = date_time.date()
  return date.strftime("%Y-%m-%d")

def plot_results(json_data, unique_name):
  """ Plotting all results of GitHub's view's .JSON files.

  Args:
    json_data: A string providing a JSON file.

  Returns:
    None: A printed file with the number of the 
          zip files where the json files has been stored.
  """

  times = []
  counts = []
  unique=[]

  for person in json_data["views"]:
    times.append(remove_time_information(person["timestamp"]))
    counts.append(person["count"])
    unique.append(person["uniques"])

  plt.bar(times, counts, color="b", label="Total")
  plt.bar(times, unique, color="r", label="Unique")
  plt.xlabel("Date")
  plt.xticks(rotation=45)
  plt.ylabel("Counts")
  plt.title("Vayesta Traffic stats")
  plt.legend()
  plt.tight_layout()
  plt.savefig(os.path.join(os.getcwd(),unique_name+".png"))
  plt.clf()

def processing_files(f, unique_name, i):
    json_data=json.load(f[i])
    plot_results(json_data, unique_name[i])
    print ("Result {}.png has been saved".format(unique_name[i]))
  
def stats_analysis():
  """Opens all zip files and the JSON file in the given folder."""

  folder_path = os.path.join(os.getcwd())
  bad_folder=os.path.join(folder_path,"vayesta.master.13102022.zip")
  os.remove(bad_folder)

  zip_files = open_zip_files(folder_path) 
  files_zip=[values.namelist()[3] for idx, values in enumerate(zip_files)]

  f=[zip_files[idx].open("data/views.json") for idx, values in enumerate(zip_files)]
  unique_name=[os.path.split(zip_files[idx].filename)[1].split(".")[2]
               for idx, values in enumerate(zip_files)]

  for i in range(len(zip_files)):
    processing_files(f, unique_name,i)

  
if __name__ == "__main__":
  stats_analysis()
