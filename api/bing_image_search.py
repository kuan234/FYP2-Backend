import requests
import matplotlib.pyplot as plt
from PIL import Image
from io import BytesIO

# Replace with your Bing API subscription key
subscription_key = "e5a0260c7437442b853327d940423691"
search_url = "https://api.bing.microsoft.com/v7.0/images/search"
search_term = "puppies"  # Change this to test with other search terms

headers = {"Ocp-Apim-Subscription-Key": subscription_key}
params = {
    "q": search_term,  # Search term
    "license": "public",  # Publicly licensed images
    "imageType": "photo"  # Image type as photo
}

try:
    # Perform the Bing Image Search API call
    response = requests.get(search_url, headers=headers, params=params)
    response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
    search_results = response.json()

    # Extract thumbnail URLs from the search results
    thumbnail_urls = [img["thumbnailUrl"] for img in search_results["value"][:16]]

    # Prepare a 4x4 grid to display the images
    fig, axes = plt.subplots(4, 4, figsize=(10, 10))
    fig.tight_layout(pad=3.0)

    # Iterate through the thumbnails and display them in the grid
    for i in range(4):
        for j in range(4):
            try:
                # Fetch and display the image
                image_data = requests.get(thumbnail_urls[i + 4 * j])
                image_data.raise_for_status()
                image = Image.open(BytesIO(image_data.content))
                axes[i][j].imshow(image)
                axes[i][j].axis("off")
            except Exception as e:
                print(f"[ERROR] Unable to fetch image {i + 4 * j}: {e}")

    # Show the images
    plt.show()

except Exception as e:
    print(f"[ERROR] An error occurred: {e}")
