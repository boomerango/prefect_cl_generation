from prefect import flow, task
from prefect.tasks import task_input_hash
from datetime import timedelta
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
import os
import PyPDF2
from prefect.filesystems import LocalFileSystem
from prefect.blocks.system import Secret
from prefect import get_run_logger
from prefect.artifacts import create_markdown_artifact
from datetime import datetime
import re
from typing import List

@task(retries=2, retry_delay_seconds=30)
def parse_cv(cv_path: str = "./cv.pdf") -> str:
    """Parse CV from PDF file"""
    try:
        # Load storage block
        storage_block = LocalFileSystem.load("cv-storage")

        # Read CV file content
        content = storage_block.read_path(cv_path)
        
        # Create a BytesIO object to work with PyPDF2
        from io import BytesIO
        pdf_file = BytesIO(content)
        
        # Parse PDF content
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        cv_text = ""
        for page in pdf_reader.pages:
            cv_text += page.extract_text()
            
        return cv_text.strip()
    except Exception as e:
        raise Exception(f"Failed to parse CV: {str(e)}")

@task(retries=0, retry_delay_seconds=60, cache_key_fn=task_input_hash, cache_expiration=timedelta(hours=1))
def scrape_job_description(url: str) -> str:
    """Scrape job description from the provided URL"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        print(f"Attempting to scrape URL: {url}")
        
        # Using the correct selector for Djinni
        container = soup.select_one('div.container.job-post-page div.col-lg-8')
        
        if container:
            print("Found job description container")
            job_description = container.get_text(strip=True, separator='\n')
            return job_description
        
        # If not found, save debug info
        with open('debug_page.html', 'w', encoding='utf-8') as f:
            f.write(soup.prettify())
        print("\nPage Title:", soup.title.string if soup.title else "No title found")
        raise Exception("Could not find job description container")
            
    except requests.RequestException as e:
        raise Exception(f"Failed to fetch URL {url}: {str(e)}")
    except Exception as e:
        raise Exception(f"Failed to scrape job description: {str(e)}")

@task(retries=2, retry_delay_seconds=30)
def generate_cover_letter(job_description: str, cv_content: str) -> str:
    """Generate a cover letter using OpenAI"""
    
    try:
        # Get OpenAI API key from environment or Secret block
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            secret_block = Secret.load("openaiapikey")
            api_key = secret_block.get()
        
        client = OpenAI(api_key=api_key)
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": f"You are a professional cover letter writer. Use the following CV information to personalize the cover letter: {cv_content}"},
                {"role": "user", "content": f"Generate a concise cover letter for the following job description, highlighting relevant experience from my CV: {job_description}"}
            ],
            max_tokens=500,
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        raise Exception(f"Failed to generate cover letter: {str(e)}")

@flow(name="Cover Letter Generator", description="Generates cover letter from job posting URL(s) and CV")
def cover_letter_workflow(job_urls_text: str, cv_path: str = "./cv.pdf", pattern: str = r'https?://djinni\.co/jobs/\d+[^\s\n]+') -> str:
    """
    Main workflow that orchestrates the cover letter generation process
    Args:
        job_urls_text: String containing URLs (one per line)
        cv_path: Path to CV file in storage
    """
    
    logger = get_run_logger()
    
    # Parse URLs from the input text
    urls_to_process = re.findall(pattern, job_urls_text)
    
    if not urls_to_process:
        raise Exception("No valid Djinni job URLs found in the input")
    
    logger.info(f"Found {len(urls_to_process)} URLs to process")
    
    cv_content = parse_cv(cv_path)
    results = []
    
    for url in urls_to_process:
        logger.info(f"Processing job URL: {url}")
        try:
            job_description = scrape_job_description(url)
            cover_letter = generate_cover_letter(job_description, cv_content)
            timestamp = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
            
            # Create artifact
            create_markdown_artifact(
                markdown=f"# Generated Cover Letter\n\n{cover_letter}",
                key=f"cover-letter-{timestamp}",
                description=f"Cover letter for job: {url}"
            )
            
            results.append(f"============================\n{url}\n\n{cover_letter}")
            
        except Exception as e:
            logger.error(f"Failed to process URL {url}: {str(e)}")
            results.append(f"============================\n{url}\n\nError: {str(e)}")
    
    # Join all results with newlines
    final_output = "\n".join(results)
    logger.info("Completed processing all URLs")
    return final_output

if __name__ == "__main__":
    # Remove the example usage as we'll be deploying this flow
    pass