import os
import requests
import numpy as np
from PIL import Image, ImageDraw
from mtcnn import MTCNN
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.hashers import check_password
from .serializers import ItemSerializer
from base.models import Employee
from deepface import DeepFace


@api_view(['GET'])
def getData(request):
    user_id = request.GET.get('user_id')  # Retrieve the user_id from query parameters
    if user_id:
        try:
            employee = Employee.objects.get(id=user_id)  # Filter by user_id
            serializer = ItemSerializer(employee)  # Serialize single object
            return Response(serializer.data)
        except Employee.DoesNotExist:
            return Response({'error': 'User not found'}, status=404)
    else:
        employee = Employee.objects.all()  # Retrieve all users if no user_id is provided
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
            employee = Employee.objects.get(email=email)
            if password == employee.password:
                # Send the employee details with the response
                return Response({
                    "message": "Login successful!",
                    "employee": {
                        "id": employee.id,
                        "email": employee.email,
                        "name": employee.name,
                    }
                }, status=200)
            else:
                return Response({"message": "Invalid Username/Password"}, status=400)

        except Employee.DoesNotExist:
            return Response({"message": "User not found"}, status=404)
        except Exception as e:
            return Response({"message": f"An error occurred: {str(e)}"}, status=500)
        
# Initialize the MTCNN detector once to avoid reloading on every request
detector = MTCNN()

# @api_view(['POST'])
# def detect_face(request):
#     if 'image' not in request.FILES:
#         return JsonResponse({'error': 'No image provided'}, status=400)

#     try:
#         # Get the uploaded image
#         image_file = request.FILES['image']
#         img = Image.open(image_file).convert('RGB')
        
#         # Get original width and height from the request
#         original_width = int(request.POST.get('width', img.width))
#         original_height = int(request.POST.get('height', img.height))
#         print(f"Original Height: {original_height}")  # Debugging resized image shape
#         print(f"Original Width: {original_width}")  # Debugging resized image shape


#         # Resize for detection
#         resized_width = 240
#         resized_height = 240
#         ratio_height = original_height / resized_height
#         ratio_weight = original_width /resized_width
#         print(f"ratio Height: {ratio_height}")  # Debugging resized image shape
#         print(f"ratio Width: {ratio_weight}") 
#         img_resized = img.resize((resized_width, resized_height))

#         # Convert image to NumPy array
#         img_array = np.array(img_resized)

#         print(f"Resized image shape: {img_array.shape}")  # Debugging resized image shape

#         # Detect faces using MTCNN
#         detections = detector.detect_faces(img_array)

#         # Extract bounding boxes and scale them back to the original size
#         faces = []
#         for detection in detections:
#             x, y, w, h = detection['box']  # x, y are the top-left corner, w and h are width and height

#             # Scale bounding box back to the original dimensions
#             scale_x = ratio_weight
#             scale_y = ratio_height

#             scaled_face = {
#                 'x': int(x  ),
#                 'y': int(y  ),
#                 'width': int(w  ),
#                 'height': int(h  ),
#             }
#             print(f"Detected face (scaled): {scaled_face}")  # Debug log
#             faces.append(scaled_face)

#         print(f"Detected faces (original scale): {faces}")  # Debugging bounding boxes
#         print(f"Num Face: {len(faces)}")  # Debugging bounding boxes
#         # Return the bounding box data along with the number of faces detected
#         return JsonResponse({
#             'face_detected': len(faces) > 0,
#             'num_faces': len(faces),
#             'faces': faces,
#         })

#     except Exception as e:
#         print("Error during face detection:", str(e))
#         return JsonResponse({'error': f'Error during face detection: {str(e)}'}, status=500)


@api_view(['POST'])
def verify_face(request):
    if 'image' not in request.FILES:
        return Response({'error': 'No image provided'}, status=400)

    try:
        # 1. Process the Captured Image
        image_file = request.FILES['image']
        img = Image.open(image_file).convert('RGB')
        original_width, original_height = img.size

        # Resize image for detection
        img_resized = img.resize((240, 240))
        img_array = np.array(img_resized)

        # Detect faces using MTCNN
        detections = detector.detect_faces(img_array)

        if len(detections) == 0:
            face = 0
            return Response({face})

        # Prepare to draw bounding boxes and crop faces
        draw = ImageDraw.Draw(img_resized)
        cropped_faces = []

        for detection in detections:
            # Bounding box in resized image
            x_resized, y_resized, width_resized, height_resized = detection['box']

            # Scale bounding box back to original image dimensions
            x = int(x_resized * original_width / 240)
            y = int(y_resized * original_height / 240)
            width = int(width_resized * original_width / 240)
            height = int(height_resized * original_height / 240)

            # Draw bounding box on resized image
            draw.rectangle(
                [(x_resized, y_resized), (x_resized + width_resized, y_resized + height_resized)], 
                outline="red", 
                width=3
            )

            # Crop face from the original image
            cropped_face = img.crop((x, y, x + width, y + height))
            cropped_faces.append(cropped_face)

        # Save the detected face image with bounding boxes
        detected_faces_path = os.path.join(settings.MEDIA_ROOT, "images", "detected_faces.jpg")
        img_resized.save(detected_faces_path)

        # Save the cropped faces temporarily
        cropped_face_paths = []
        for i, cropped_face in enumerate(cropped_faces):
            cropped_face_path = os.path.join(settings.MEDIA_ROOT, "images", f"cropped_face_{i}.jpg")
            cropped_face.save(cropped_face_path)
            cropped_face_paths.append(cropped_face_path)

        # 2. Retrieve the Reference Image from Database
        user_id = request.POST.get('user_id')
        print(f"[DEBUG] user ID: {user_id}")

        if not user_id:
            return Response({'error': 'user_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        user = Employee.objects.filter(id=user_id).first()
        if not user:
            return Response({'error': 'User not found'}, status=404)

        if not user.faceImage:
            return Response({'error': 'Face image not found for this user'}, status=404)
        
        print(f"[DEBUG] user image: {user.faceImage}")

        reference_image_path = os.path.join(settings.MEDIA_ROOT, "images", str(user.faceImage))  # Adjust path if needed
        print(f"[DEBUG] reference_image_path: {reference_image_path}")

        # 3. Face Verification Using DeepFace
        verification_results = []
        for face_path in cropped_face_paths:
            try:
                result = DeepFace.verify(
                    img1_path=face_path, # Crop Image
                    img2_path=reference_image_path, # User Face Image in Database
                    model_name="Facenet",  # or "VGG-Face"
                    enforce_detection=False
                )
                verification_results.append({
                    'face_path': face_path,
                    'verified': result['verified'],
                    'distance': result['distance'],
                    'threshold': result['threshold'],
                    'similarity': 1 - result['distance'],  # Calculate similarity
                })
                print(f"[DEBUG] Result: {verification_results}")
                detected_image_path = "/media/images/detected_faces.jpg"
                print(f"[DEBUG] detected_image_path: {detected_image_path}")



            except Exception as e:
                print(f"Error verifying face {face_path} against reference: {e}")
                verification_results.append({'face_path': face_path, 'error': str(e)})

        # Return Response
        return Response({
            'message': 'Face(s) detected and verification performed successfully',
            'faces_detected': len(detections),
            'verification_results': verification_results,
            'detected_image_path': detected_image_path,  # Relative path for accessing the image,
            'similarity': verification_results
        })

    except Exception as e:
        print("Error during face verification:", str(e))
        return Response({'error': f'Error during face verification: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
