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
    date_string: A string representing a date in the 
    format 2022-10-03T00:00:00Z.

  Returns:
     A string representing the date without the time information, 
     in the format 2022-10-03.
  """
  import datetime
  
  date_time = datetime.datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%SZ")
  date = date_time.date()
  return date.strftime("%Y-%m-%d")

def sorting_list(my_list):
  
  unique=list(set([i for i in my_list]))
  return sorted(unique, key=lambda x: x[0])
  
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

def cumulative_stats(zip_files, f):
  """ Cummulative distribution of views for a GitHub  
      traffic repository stats.
  """
  import numpy as np
  
  total_views=[]
  unique_views=[]
  times=[]
  for i in range(len(zip_files)):
    json_data=json.load(f[i])
    total_views.append(json_data["count"])
    unique_views.append(json_data["uniques"])
    times.append(remove_time_information(json_data["views"][0]["timestamp"]))

  #Cumulative total views
  tot_views_list = sorting_list(list(zip(times, total_views)))
  time, tot_views = zip(*tot_views_list)  
  tot_views_sum=np.cumsum(np.array(tot_views))
  

  #Unique views
  uniq_list=sorting_list(list(zip(times, unique_views)))
  time_same, unq_views = zip(*uniq_list)  
  unq_views_sum=np.cumsum(np.array(unq_views))
  
  #Organised time intervals of the artifacts from GitHub
  times=np.array(time)
  
  plt.bar(times, tot_views_sum, color="b", label="Total")
  plt.bar(times, unq_views_sum, color="r", label="Unique")
  plt.xlabel("Time interval")
  plt.xticks(rotation=45)
  plt.ylabel("Counts")
  plt.title("Vayesta Traffic (views) stats")
  plt.legend()
  plt.tight_layout()
  plt.savefig(os.path.join(os.getcwd(),"cumulative_counts.png"))

def processing_files(f, unique_name, i):
    json_data=json.load(f[i])
    plot_results(json_data, unique_name[i])
    print ("Result {}.png has been saved".format(unique_name[i]))
  
def stats_analysis(cumulative=True):
  """Opens all zip files and the JSON file in the 
     given folder.
  """

  folder_path = os.path.join(os.getcwd())
  bad_folder=os.path.join(folder_path,"vayesta.master.13102022.zip")
  os.remove(bad_folder)
  
  zip_files = open_zip_files(folder_path) 
  files_zip=[values.namelist()[3] for idx, values in enumerate(zip_files)]

  f=[zip_files[idx].open("data/views.json") for idx, values in enumerate(zip_files)]
  unique_name=[os.path.split(zip_files[idx].filename)[1].split(".")[2]
               for idx, values in enumerate(zip_files)]

  if cumulative:
    cumulative_stats(zip_files, f)

  if not cumulative:
    for i in range(len(zip_files)):
      processing_files(f, unique_name,i)
  
if __name__ == "__main__":
  stats_analysis()
