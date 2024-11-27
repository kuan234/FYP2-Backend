import os
import requests
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .serializers import ItemSerializer
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.contrib.auth.hashers import check_password
from base.models import Employee
from PIL import Image
import requests

@api_view(['GET'])
def getData(request):
    employee = Employee.objects.all()
    serializer = ItemSerializer(employee, many=True)
    return Response(serializer.data)

@api_view(['POST'])
def addEmployee(request):
    serializer = ItemSerializer(data = request.data)
    if serializer.is_valid():
        serializer.save()
    return Response()

@api_view(['POST'])
def login_view(request):
    if request.method == 'POST':
        email = request.data.get('email')
        password = request.data.get('password')

        try:
            # Get the employee by email
            employee = Employee.objects.get(email=email)

            # Directly compare plain text password with stored plain text password
            if password == employee.password:
                return Response({"message": "Login successful!"}, status=200)
            else:
                return Response({"message": "Invalid credentials"}, status=400)

        except Employee.DoesNotExist:
            return Response({"message": "User not found"}, status=404)
        except Exception as e:
            return Response({"message": f"An error occurred: {str(e)}"}, status=500)
# # Bing API Configuration
# BING_API_KEY = "e5a0260c7437442b853327d940423691"
# BING_ENDPOINT = "https://api.bing.microsoft.com/v7.0/images/visualsearch"


# def resize_image(img_path, output_path, max_width=1920, max_height=1080):
#     """
#     Resize an image to ensure dimensions are within the specified limits.

#     Args:
#         img_path (str): Path to the original image.
#         output_path (str): Path to save the resized image.
#         max_width (int): Maximum allowed width (default: 1920 pixels).
#         max_height (int): Maximum allowed height (default: 1080 pixels).
#     Returns:
#         str: Path to the resized image.
#     """
#     with Image.open(img_path) as img:
#         img_format = img.format  # Preserve original format
#         width, height = img.size

#         # Calculate scaling factor
#         scaling_factor = min(max_width / width, max_height / height, 1.0)
#         new_width = int(width * scaling_factor)
#         new_height = int(height * scaling_factor)

#         # Resize and save the image
#         img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
#         img.save(output_path, format=img_format)
#         print(f"[DEBUG] Resized image saved at: {output_path}")
#         print(f"[DEBUG] Resized image dimensions: {new_width}x{new_height}")
#         return output_path


# def compress_image(img_path, output_path, max_size=4*1024*1024, quality=85):
#     """
#     Compress an image to ensure it is under the specified size.

#     Args:
#         img_path (str): Path to the original image.
#         output_path (str): Path to save the compressed image.
#         max_size (int): Maximum allowed size in bytes (default: 4MB).
#         quality (int): Quality for JPEG compression (default: 85).
#     Returns:
#         str: Path to the compressed image.
#     """
#     with Image.open(img_path) as img:
#         img_format = img.format  # Preserve original format

#         # Reduce quality iteratively until size is below max_size
#         while os.path.getsize(img_path) > max_size:
#             img.save(output_path, format=img_format, quality=quality)
#             if quality <= 10:  # Prevent infinite loop if quality too low
#                 break
#             quality -= 10  # Reduce quality further

#         print(f"[DEBUG] Compressed image saved at: {output_path}")
#         print(f"[DEBUG] Compressed image size: {os.path.getsize(output_path)} bytes")
#         return output_path


# @api_view(['POST'])
# def uploadImage(request):
#     if 'image' not in request.FILES:
#         return Response({"error": "No image file provided."}, status=status.HTTP_400_BAD_REQUEST)

#     try:
#         # Save the uploaded image
#         image = request.FILES['image']
#         image_instance = ImageModel(image_path=image)
#         image_instance.save()

#         original_img_path = os.path.join(settings.MEDIA_ROOT, image_instance.image_path.name)
#         if not os.path.exists(original_img_path):
#             print(f"[ERROR] Image path does not exist: {original_img_path}")
#             return Response({"error": "Image file not saved correctly."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#         print(f"[DEBUG] Reading image from: {original_img_path}")

#         # Check image size and format
#         image_size = os.path.getsize(original_img_path)
#         with Image.open(original_img_path) as img:
#             image_format = img.format
#             image_dimensions = img.size

#         print(f"[DEBUG] Image format: {image_format}")
#         print(f"[DEBUG] Image size: {image_size} bytes")
#         print(f"[DEBUG] Image dimensions: {image_dimensions}")

#         # File path for resized/compressed image
#         processed_img_path = os.path.join(settings.MEDIA_ROOT, "processed_images", image_instance.image_path.name)

#         # Resize or compress image if too large
#         if image_size > 4 * 1024 * 1024 or max(image_dimensions) > 1920:
#             print("[DEBUG] Resizing or compressing image...")
#             os.makedirs(os.path.dirname(processed_img_path), exist_ok=True)
#             resize_image(original_img_path, processed_img_path, max_width=1920, max_height=1080)

#             # Compress if still too large
#             if os.path.getsize(processed_img_path) > 4 * 1024 * 1024:
#                 compress_image(processed_img_path, processed_img_path)
#         else:
#             processed_img_path = original_img_path

#         # Call Bing Visual Search API with the processed image
#         with open(processed_img_path, "rb") as image_fd:
#             headers = {"Ocp-Apim-Subscription-Key": BING_API_KEY}
#             files = {"image": image_fd}

#             print("[DEBUG] Sending image to Bing Visual Search API...")
#             response = requests.post(BING_ENDPOINT, headers=headers, files=files)
#             print(f"[DEBUG] API Response Status Code: {response.status_code}")

#             if response.status_code != 200:
#                 print("[ERROR] Response Content:", response.text)
#                 response.raise_for_status()

#             result = response.json()

#             if not result or "tags" not in result:
#                 return Response({"error": "No visual search results found."}, status=status.HTTP_204_NO_CONTENT)

#             # Process results
#             extracted_products = extract_product_titles(result)
            
#             # Print results in the console
#             print("\n[DEBUG] API Results:")
#             for idx, product in enumerate(extracted_products, start=1):
#                 print(f"{idx}. Title: {product['title']}")
#                 print(f"   Redirect URL: {product['redirect_url']}")
#                 print(f"   Action Type: {product['action_type']}")
#                 print("-" * 40)

#             return Response({
#                 "message": "Image processed successfully.",
#                 "products": extracted_products
#             }, status=status.HTTP_200_OK)
        
    
#     except Exception as e:
#         print("[ERROR] General Error:", e)
#         return Response({"error": "An error occurred while processing the image.", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# def extract_product_titles(result):
#     """
#     Extract product titles and related information from the Bing Visual Search API response.

#     Args:
#         result (dict): Parsed JSON response from the Bing API.
#     Returns:
#         list: List of dictionaries containing product information.
#     """
#     products = []
#     if "tags" in result:
#         for tag in result["tags"]:
#             if "actions" in tag:
#                 for action in tag["actions"]:
#                     if "data" in action and "value" in action["data"]:
#                         for value_item in action["data"]["value"]:
#                             product_name = value_item.get("name", "Unknown Title")
#                             redirect_url = value_item.get("webSearchUrl", "")
#                             products.append({
#                                 "title": product_name,
#                                 "redirect_url": redirect_url,
#                                 "action_type": action.get("actionType", "Unknown Action Type")
#                             })
#     return products
