import aiohttp
import asyncio
import json

# --- CONFIGURATION ---
DOIS = [
    "https://doi.org/10.1145/3366423.3380250",
    "https://doi.org/10.1038/s41586-020-2649-2",
    "https://doi.org/10.48550/arXiv.2305.13059",
    "https://doi.org/10.1007/978-3-031-26390-3_9",
    "https://doi.org/10.14778/3476311.3476325"
    # Add more DOIs here...
]

FIELDS = "id,doi,title,cited_by_count,abstract_inverted_index"
CONCURRENT_REQUESTS = 3  # Safe concurrency limit (adjust as needed)
OUTPUT_FILE = "doi_async_with_abstracts.json"


# --- ABSTRACT PARSING FUNCTION ---
def reconstruct_abstract(inverted_index):
    """Reconstruct plain-text abstract from inverted index."""
    if not inverted_index:
        return None  # Handle case where abstract is None

    # Build position -> word mapping
    position_word = {}
    for word, positions in inverted_index.items():
        for pos in positions:
            position_word[pos] = word

    # Sort positions and form abstract
    abstract_words = [word for _, word in sorted(position_word.items())]
    return " ".join(abstract_words)


# --- FETCHING FUNCTION ---
async def fetch_work(session, doi):
    url = f"https://api.openalex.org/works/https://doi.org/{doi}?select={FIELDS}"
    async with session.get(url) as response:
        if response.status == 200:
            print(f"Fetched: {doi}")
            data = await response.json()

            # Reconstruct abstract if available
            abstract_plain = reconstruct_abstract(data.get("abstract_inverted_index"))

            # Add plain-text abstract to output
            return {
                "id": data.get("id"),
                "doi": data.get("doi"),
                "title": data.get("title"),
                "cited_by_count": data.get("cited_by_count"),
                "abstract": abstract_plain
            }
        else:
            print(f"Failed to fetch {doi}: {response.status}")
            return None


# --- SEMAPHORE WRAPPER TO LIMIT CONCURRENCY ---
async def bound_fetch(semaphore, session, doi):
    async with semaphore:
        return await fetch_work(session, doi)


# --- MAIN ASYNC FUNCTION ---
async def main(dois):
    semaphore = asyncio.Semaphore(CONCURRENT_REQUESTS)
    async with aiohttp.ClientSession() as session:
        tasks = [bound_fetch(semaphore, session, doi) for doi in dois]
        results = await asyncio.gather(*tasks)
    return [res for res in results if res is not None]  # Remove failed queries


# --- EXECUTION ---
if __name__ == "__main__":
    results = asyncio.run(main(DOIS))
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4)
    print(f"Saved {len(results)} works to '{OUTPUT_FILE}'")
