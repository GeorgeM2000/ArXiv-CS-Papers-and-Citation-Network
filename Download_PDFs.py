import aiohttp
import asyncio
#import pikepdf
import os
import time
#from PyPDF2 import PdfReader, PdfWriter
#from io import BytesIO
from collections import defaultdict, Counter


# If the number of papers to be downloaded is large, download a number of papers in separate directories
paper_dirs = ['Papers 1', 'Papers 2', 'Papers 3', 'Papers 4', 'Papers 5', 'Papers 6']

SAVE_DIR = "Papers 7"
empty_papers = []
papers_with_incorrect_type = []
failed_papers = []
erroneous_papers = []
LIMIT = 9000 # Limit the number of papers to be downloaded



async def download_pdf(session, paper_id, semaphore):
    async with semaphore:  # Limit concurrent requests
        try:
            async with session.get(f"https://arxiv.org/pdf/{paper_id}") as response:
                if response.status == 200:
                    content = await response.read()
                    content_type = response.headers.get("Content-Type", "")
                    if content:
                        if "pdf" in content_type.lower():
                            if "/" in paper_id:
                                paper_id = paper_id.replace("/", "_")
                            
                            with open(f'{SAVE_DIR}/{paper_id}.pdf', "wb") as f:
                                f.write(content)
                        else:
                            print(f'{paper_id} has incorrect content type')
                            papers_with_incorrect_type.append(paper_id)
                    else:
                        print(f'Empty {paper_id}')
                        empty_papers.append(paper_id)
                else:
                    print(f'Failed {paper_id} status {response.status}')
                    failed_papers.append((paper_id, response.status))
        except Exception as e:
            print(f"Error downloading {paper_id}: {e}")
            erroneous_papers.append(paper_id)


def check_for_duplicates():
    filename_map = defaultdict(list)
    filenames_with_underscore = [0, []]

    for directory in paper_dirs:
        for filename in os.listdir(directory):
            if filename.endswith(".pdf"):
                if "_" in filename:
                    processed_name = filename.replace("_", "/").replace(".pdf", "")
                    filenames_with_underscore[0] += 1
                    filenames_with_underscore[1].append(processed_name)
                else:
                    processed_name = filename.replace(".pdf", "")
                
                filename_map[processed_name].append(filename)
            else:
                print(f'{filename} does not end with .pdf')

    print(f'Filenames with an underscore: {filenames_with_underscore[0]} \nTotal filenames: {len(filename_map)}\n')
    
    # Find duplicates (i.e., processed names with multiple original filenames)
    duplicates = {key: value for key, value in filename_map.items() if len(value) > 1}

    if duplicates:
        print("🔴 Duplicate detected:")
        for key, files in duplicates.items():
            print(f"Processed Name: {key} → Original Files: {files}")
    else:
        print("✅ No duplicates found!")

    return filenames_with_underscore[1]


def check_validity(existing_papers, paper_ids):
    # Check if there are papers downloaded that do not exist in the node list
    true_positives = [0, 0]
    missing_papers = [[], []]
    filenames_with_slash = []
    for epaper_id in existing_papers:
        if epaper_id in paper_ids:
            true_positives[0] += 1
        else:
            missing_papers[0].append(epaper_id)

    print(f'There are {true_positives[0]} papers that match the paper IDs in the node list')
    
    if missing_papers[0]:
        print(f'{len(missing_papers[0])} papers do not exist in the node list')
        print(missing_papers[0])

    # Check if there are papers in the node list that were not downloaded
    for paper_id in paper_ids:
        if paper_id in existing_papers:
            true_positives[1] += 1
            if "/" in paper_id:
                filenames_with_slash.append(paper_id)
        else:
            missing_papers[1].append(paper_id)

    print(f'There are {true_positives[1]} papers that were successfully downloaded')
    
    if missing_papers[1]:
        print(f'{len(missing_papers[1])} papers were not downloaded')
        print(missing_papers[1])
    
    return filenames_with_slash
    

def get_missing_paper_ids(id_file, filenames_with_underscore):
    with open(id_file, "r") as f:
        paper_ids = {line.strip() for line in f}  # Use a set for faster lookups

    print(f'Paper IDs (before): {len(paper_ids)}')

    existing_papers = {
        filename.replace("_", "/").replace(".pdf", "")
        for directory in paper_dirs 
        for filename in os.listdir(directory)
        if filename.endswith(".pdf")
    }

    filenames_with_slash = check_validity(existing_papers, paper_ids)

    if Counter(filenames_with_slash) == Counter(filenames_with_underscore):
        print("✅ The paper IDs with a '/' in the node list are the same as the paper IDs with an underscore in the downloaded papers")

    paper_ids = list(paper_ids - existing_papers)

    print(f'Paper IDs (after): {len(paper_ids)}'); print(f'Existing papers: {len(existing_papers)}')
    
    return paper_ids 


async def download_all_papers(id_file, filenames_with_underscore, max_concurrent_downloads=15):
    paper_ids = get_missing_paper_ids(id_file, filenames_with_underscore)
    semaphore = asyncio.Semaphore(max_concurrent_downloads)  # Limit concurrency
    async with aiohttp.ClientSession() as session:
        tasks = [download_pdf(session, paper_id, semaphore) for paper_id in paper_ids]
        await asyncio.gather(*tasks)  # Run all downloads in parallel



if __name__ == '__main__':

    filenames_with_underscore = check_for_duplicates()

    # Directory to save PDFs
    #os.makedirs(SAVE_DIR, exist_ok=True)


    # Run the script
    id_file = "graph-v2/Node_IDs.txt" 
    asyncio.run(download_all_papers(id_file, filenames_with_underscore))


    # === Save IDs of failed papers ===
    with open("Empty_Papers.txt", 'w') as f:
        for paper_id in empty_papers:
            f.write(f'{paper_id}\n')

    with open("Papers_with_Incorrect_Type.txt", 'w') as f:
        for paper_id in papers_with_incorrect_type:
            f.write(f'{paper_id}\n')
            
    with open("Failed_Papers.txt", 'w') as f:
        for paper_id in failed_papers:
            f.write(f'{paper_id}\n')

    with open("Erroneous_Papers.txt", 'w') as f:
        for paper_id in erroneous_papers:
            f.write(f'{paper_id}\n')
