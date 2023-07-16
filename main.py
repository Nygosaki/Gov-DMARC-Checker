import subprocess
import re
import urllib.request
import csv
import traceback
import multiprocessing


# Function to write data to a CSV file
def write_to_csv(queue):
    # Open the CSV file in write mode
    with open('demo_file.csv', 'w', newline='') as dmarc_csv:
        writer = csv.writer(dmarc_csv)

        # Write the header row
        writer.writerow([
            'Domain', 'Type', 'Agency', 'Organization', 'City', 'State', 'Security Contact Email',
            'v', 'p', 'sp', 'pct', 'adkim', 'aspf', 'fo', 'ruf', 'rua', 'rf', 'ri'
        ])

        # Continuously get items from the queue and write them to the CSV file
        while True:
            item = queue.get()
            if item is None:
                break
            writer.writerow(item)


# Main function for processing domain information
def main_proc(queue, domaininfo_decoded):
    try:
        dmarc_sort = dict()
        domaininfo_split = re.split(",", domaininfo_decoded)
        dmarc_sort["Domain"] = domaininfo_split[0]

        # Check if the current line is the header row, if not, process the data
        if dmarc_sort["Domain"] != "Domain Name":
            try:
                dmarc_sort["Type"] = domaininfo_split[1]
            except:
                dmarc_sort["Type"] = "null"
            try:
                dmarc_sort["Agency"] = domaininfo_split[2]
            except:
                dmarc_sort["Agency"] = "null"
            try:
                dmarc_sort["Organization"] = domaininfo_split[3]
            except:
                dmarc_sort["Organization"] = "null"
            try:
                dmarc_sort["City"] = domaininfo_split[4]
            except:
                dmarc_sort["City"] = "null"
            try:
                dmarc_sort["State"] = domaininfo_split[5]
            except:
                dmarc_sort["State"] = "null"
            try:
                dmarc_sort["Security Contact Email"] = domaininfo_split[6].replace("\n", "")
            except:
                dmarc_sort["Security Contact Email"] = "null"
        else:
            return ()

        # Perform nslookup to retrieve DMARC record information
        nslookup_result = subprocess.run(f"nslookup -type=txt _dmarc.{dmarc_sort['Domain']}",
                                         capture_output=True).stdout.decode()

        # Extract relevant DMARC record values using regular expressions
        try:
            dmarc_raw = re.findall('"(.*?)"', nslookup_result)[0] + " "
        except:
            dmarc_raw = "v=null"

        # Process and store the DMARC record values
        try:
            dmarc_sort["v"] = re.findall('v=(.*?)[; \n]', dmarc_raw)[0]
        except:
            dmarc_sort["v"] = "null"
        if dmarc_sort["v"] != "null":
            try:
                dmarc_sort["p"] = re.findall('p=(.*?)[; \n]', dmarc_raw)[0]
            except:
                dmarc_sort["p"] = "error"
            try:
                dmarc_sort["sp"] = re.findall('sp=(.*?)[; \n]', dmarc_raw)[0]
            except:
                dmarc_sort["sp"] = dmarc_sort["p"]
            try:
                dmarc_sort["pct"] = re.findall('pct=(.*?)[; \n]', dmarc_raw)[0]
            except:
                dmarc_sort["pct"] = "100"
            try:
                dmarc_sort["adkim"] = re.findall('adkim=(.*?)[; \n]', dmarc_raw)[0]
            except:
                dmarc_sort["adkim"] = "r"
            try:
                dmarc_sort["aspf"] = re.findall('aspf=(.*?)[; \n]', dmarc_raw)[0]
            except:
                dmarc_sort["aspf"] = "r"
            try:
                dmarc_sort["fo"] = re.findall('fo=(.*?)[; \n]', dmarc_raw)[0]
            except:
                dmarc_sort["fo"] = "0"
            try:
                dmarc_sort["ruf"] = re.findall('ruf=(.*?)[; \n]', dmarc_raw)[0]
            except:
                dmarc_sort["ruf"] = "none"
            try:
                dmarc_sort["rua"] = re.findall('rua=(.*?)[; \n]', dmarc_raw)[0]
            except:
                dmarc_sort["rua"] = "none"
            try:
                dmarc_sort["rf"] = re.findall('rf=(.*?)[; \n]', dmarc_raw)[0]
            except:
                dmarc_sort["rf"] = "afrf"
            try:
                dmarc_sort["ri"] = re.findall('ri=(.*?)[; \n]', dmarc_raw)[0]
            except:
                dmarc_sort["ri"] = "86400"

        # Put the values into the queue for writing to the CSV file
        queue.put(dmarc_sort.values())

        # Print the processed data
        print(dmarc_sort)

    # Handle any exceptions that occur during processing
    except Exception as e:
        print(f"Error on line {domaininfo_decoded}")
        print(e)
        traceback.print_exc()


# Function to scrape military domains and process their information
def mil_domain_get(url, queue):
    print(url)

    # Read the webpage content
    mil_webpage = urllib.request.urlopen(url).read()

    # Extract the relevant HTML sections containing domain information
    mil_html = re.findall(r'<div class="DGOVListLink.*?"><a(.*?)</a>', str(mil_webpage))

    # Process each HTML section to retrieve domain information
    for i in mil_html:
        try:
            # Extract the URL, domain, and department information
            mil_url = re.findall(r'href="(.*?)"', i)[0]
            mil_domain = re.findall(r'(?:https?://)?.*?([a-z0-9\-]+\.[a-z0-9\-]+)(?:$|/)', mil_url)[0]
            mil_department = re.findall(r'">(.*?);', i + ";")[0]

            # Construct a line of data for the military domain
            mil_line = f"{mil_domain},Military,Department of Defense,{mil_department},null,null,null"

            # Invoke the main processing function for the military domain
            pool.apply(main_proc, args=(queue, mil_line))

        # Handle any exceptions that occur during processing
        except:
            print(f"Issue formatting line {i}")
            traceback.print_exc()


if __name__ == '__main__':
    # Create a multiprocessing manager and a queue for inter-process communication
    manager = multiprocessing.Manager()
    queue = manager.Queue()

    # Start a separate process for writing data to the CSV file
    writer_process = multiprocessing.Process(target=write_to_csv, args=(queue,))
    writer_process.start()

    # Create a multiprocessing pool for concurrent processing
    pool = multiprocessing.Pool()

    # Process each line from the URL containing domain information
    for line in urllib.request.urlopen("https://raw.githubusercontent.com/cisagov/dotgov-data/main/current-full.csv"):
        domaininfo_raw = line.decode('utf-8')
        pool.apply(main_proc, args=(queue, domaininfo_raw))

    # Scrape and process domain information for military domains
    mil_scrapedomains = [
        "https://www.defense.gov/Resources/Military-Departments/A-Z-List/",
        "https://www.defense.gov/Resources/Military-Departments/A-Z-List/?page=B",
        "https://www.defense.gov/Resources/Military-Departments/A-Z-List/?page=C",
        "https://www.defense.gov/Resources/Military-Departments/A-Z-List/?page=D",
        "https://www.defense.gov/Resources/Military-Departments/A-Z-List/?page=E",
        "https://www.defense.gov/Resources/Military-Departments/A-Z-List/?page=F",
        "https://www.defense.gov/Resources/Military-Departments/A-Z-List/?page=G",
        "https://www.defense.gov/Resources/Military-Departments/A-Z-List/?page=H",
        "https://www.defense.gov/Resources/Military-Departments/A-Z-List/?page=I",
        "https://www.defense.gov/Resources/Military-Departments/A-Z-List/?page=K",
        "https://www.defense.gov/Resources/Military-Departments/A-Z-List/?page=L",
        "https://www.defense.gov/Resources/Military-Departments/A-Z-List/?page=M",
        "https://www.defense.gov/Resources/Military-Departments/A-Z-List/?page=N",
        "https://www.defense.gov/Resources/Military-Departments/A-Z-List/?page=O",
        "https://www.defense.gov/Resources/Military-Departments/A-Z-List/?page=P",
        "https://www.defense.gov/Resources/Military-Departments/A-Z-List/?page=Q",
        "https://www.defense.gov/Resources/Military-Departments/A-Z-List/?page=R",
        "https://www.defense.gov/Resources/Military-Departments/A-Z-List/?page=S",
        "https://www.defense.gov/Resources/Military-Departments/A-Z-List/?page=T",
        "https://www.defense.gov/Resources/Military-Departments/A-Z-List/?page=U",
        "https://www.defense.gov/Resources/Military-Departments/A-Z-List/?page=V",
        "https://www.defense.gov/Resources/Military-Departments/A-Z-List/?page=W",
        "https://www.defense.gov/Resources/Military-Departments/A-Z-List/?page=X",
        "https://www.defense.gov/Resources/Military-Departments/A-Z-List/?page=Y",
        "https://www.defense.gov/Resources/Military-Departments/A-Z-List/?page=Z",
        "https://www.defense.gov/Resources/Military-Departments/A-Z-List/?page=0-9"
    ]
    for i in mil_scrapedomains:
        mil_domain_get(i, queue)

    # Add a None value to the queue to signal the end of processing
    queue.put(None)

    # Close the multiprocessing pool and wait for all processes to finish
    pool.close()
    pool.join()
    writer_process.join()
