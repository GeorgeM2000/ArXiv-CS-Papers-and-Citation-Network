import aiohttp
import asyncio
#import pikepdf
import os
import time
#from PyPDF2 import PdfReader, PdfWriter
#from io import BytesIO
from collections import defaultdict



paper_dirs = ['Papers 1', 'Papers 2', 'Papers 3', 'Papers 4', 'Papers 5', 'Papers 6']

SAVE_DIR = "Papers 7"
empty_papers = []
papers_with_incorrect_type = []
failed_papers = []
erroneous_papers = []
LIMIT = 9000



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
    # Dictionary to track original filenames for each processed name
    filename_map = defaultdict(list)

    for directory in paper_dirs:
        for filename in os.listdir(directory):
            if filename.endswith(".pdf"):
                processed_name = filename.replace("_", "/").replace(".pdf", "")
                filename_map[processed_name].append(filename)

    # Find duplicates (i.e., processed names with multiple original filenames)
    duplicates = {key: value for key, value in filename_map.items() if len(value) > 1}

    if duplicates:
        print("🔴 Duplicate detected:")
        for key, files in duplicates.items():
            print(f"Processed Name: {key} → Original Files: {files}")
    else:
        print("✅ No duplicates found!")


def check_validity(existing_papers, paper_ids):
    true_positives = 0
    missing_papers = []
    for epaper_id in existing_papers:
        if epaper_id in paper_ids:
            true_positives += 1
        else:
            missing_papers.append(epaper_id)

    print(f'There are {true_positives} papers that match the paper IDs in the node list')
    if missing_papers:
        print(missing_papers)
    

def get_missing_paper_ids(id_file):
    with open(id_file, "r") as f:
        paper_ids = {line.strip() for line in f}  # Use a set for faster lookups

    print(f'Paper IDs (before): {len(paper_ids)}')

    existing_papers = {
        filename.replace("_", "/").replace(".pdf", "")
        for directory in paper_dirs 
        for filename in os.listdir(directory)
        if filename.endswith(".pdf")
    }

    check_validity(existing_papers, paper_ids)

    paper_ids = list(paper_ids - existing_papers)

    print(f'Paper IDs (after): {len(paper_ids)}'); print(f'Existing papers: {len(existing_papers)}')
    
    return paper_ids 


async def download_all_papers(id_file, max_concurrent_downloads=15):
    paper_ids = get_missing_paper_ids(id_file)
    #time.sleep(30)
    semaphore = asyncio.Semaphore(max_concurrent_downloads)  # Limit concurrency
    async with aiohttp.ClientSession() as session:
        tasks = [download_pdf(session, paper_id, semaphore) for paper_id in paper_ids]
        await asyncio.gather(*tasks)  # Run all downloads in parallel



if __name__ == '__main__':

    check_for_duplicates()

    # Directory to save PDFs
    os.makedirs(SAVE_DIR, exist_ok=True)


    # Run the script
    id_file = "graph-v2/Node_IDs.txt" 
    asyncio.run(download_all_papers(id_file))


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
