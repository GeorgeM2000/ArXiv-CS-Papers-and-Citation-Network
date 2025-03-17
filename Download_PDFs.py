import aiohttp
import asyncio
#import pikepdf
import os
#from PyPDF2 import PdfReader, PdfWriter
#from io import BytesIO

SAVE_DIR = "CS_Papers"
empty_papers = []
papers_with_incorrect_type = []
failed_papers = []
erroneous_papers = []



async def download_pdf(session, paper_id, semaphore):
    async with semaphore:  # Limit concurrent requests
        try:
            async with session.get(f"https://arxiv.org/pdf/{paper_id}") as response:
                if response.status == 200:
                    content = await response.read()
                    content_type = response.headers.get("Content-Type", "")
                    if content:
                        if "pdf" in content_type.lower():
                            with open(f'{SAVE_DIR}/{paper_id}.pdf', "wb") as f:
                                f.write(content)
                        else:
                            papers_with_incorrect_type.append(paper_id)
                    else:
                        empty_papers.append(paper_id)
                else:
                    failed_papers.append((paper_id, response.status))
        except Exception as e:
            print(f"Error downloading {paper_id}: {e}")
            erroneous_papers.append(paper_id)

def get_missing_paper_ids(id_file, save_dir):
    with open(id_file, "r") as f:
        paper_ids = {line.strip() for line in f}  # Use a set for faster lookups

    # Get all filenames in the save directory (strip ".pdf" to match paper IDs)
    existing_papers = {filename.replace(".pdf", "") for filename in os.listdir(save_dir) if filename.endswith(".pdf")}

    paper_ids = list(paper_ids - existing_papers)

    print(f'Paper IDs: {len(paper_ids)}'); print(f'Existing papers: {len(existing_papers)}')
    
    return paper_ids # Convert back to a list


async def download_all_papers(id_file, max_concurrent_downloads=10):
    paper_ids = get_missing_paper_ids(id_file, SAVE_DIR)

    semaphore = asyncio.Semaphore(max_concurrent_downloads)  # Limit concurrency
    async with aiohttp.ClientSession() as session:
        tasks = [download_pdf(session, paper_id, semaphore) for paper_id in paper_ids]
        await asyncio.gather(*tasks)  # Run all downloads in parallel



if __name__ == '__main__':

    # Directory to save PDFs
    #os.makedirs(SAVE_DIR, exist_ok=True)

    # Run the script
    id_file = "graph-v2/Node_IDs.txt"  # Update with your actual file
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
