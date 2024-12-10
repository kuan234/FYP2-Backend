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
from rest_framework.parsers import MultiPartParser
from .serializers import EmployeeSerializer, AttendanceSerializer
from base.models import Employee 
from deepface import DeepFace
from base.models import AttendanceLog
from datetime import datetime, time
import uuid
 
# Get employee data
@api_view(['GET'])
def getData(request):
    user_id = request.GET.get('user_id')  # Retrieve the user_id from query parameters
    if user_id:
        try:
            employee = Employee.objects.get(id=user_id)  # Filter by user_id
            serializer = EmployeeSerializer(employee)  # Serialize single object
            return Response(serializer.data)
        except Employee.DoesNotExist:
            return Response({'error': 'User not found'}, status=404)
    else:
        employee = Employee.objects.all()  # Retrieve all users if no user_id is provided
        serializer = EmployeeSerializer(employee, many=True)
        return Response(serializer.data)

@api_view(['POST'])
def add_employee(request):
    try:
        if 'image' not in request.FILES:
            print(f"[DEBUG] No image")
            image_face = None
        else:
            image_face = request.FILES['image']
        
        print(f"[DEBUG] image: {image_face}")
        serializer = EmployeeSerializer(data=request.data)
        if serializer.is_valid():
            employee = serializer.save()
            if image_face:
                employee.faceImage = image_face
                employee.save()
            return Response({"message": "Employee added successfully!", "id": employee.id}, status=201)
        print(f"[DEBUG] Serializer errors: {serializer.errors}")  # Log errors for debugging
        return Response(serializer.errors, status=400)
    except Exception as e:
        return Response({"message": f"An error occurred: {str(e)}"}, status=500)


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

     
@api_view(['GET'])
def get_attendance_by_date(request):
    # Get the date from the query parameters
    date_str = request.GET.get('date')
    user_id = request.GET.get('user_id')  # Get user_id from the request

    if not user_id:
        print(f"[DEBUG] Not User ID")
        return Response({'error': 'User ID is required'}, status=400)

    if not date_str:
        print(f"[DEBUG] Not Date")
        return Response({'error': 'Date is required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        print(f"[DEBUG] Invalid Date format")
        return Response({'error': 'Invalid date format, use YYYY-MM-DD'}, status=status.HTTP_400_BAD_REQUEST)

    # Fetch attendance records for the selected date
    attendances = AttendanceLog.objects.filter(employee_id=user_id, date=selected_date)

    if not attendances.exists():
        return Response({'message': 'No attendance logs found for this date'}, status=status.HTTP_404_NOT_FOUND)

    # Serialize the attendance data
    attendance_data = []
    for attendance in attendances:
        check_in_time = attendance.check_in_time.strftime('%H:%M:%S')
        
        # Check if check_out_time is available
        if attendance.check_out_time:
            check_out_time = attendance.check_out_time.strftime('%H:%M:%S')
            total_hours = attendance.calculate_total_hours()
        else:
            check_out_time = 'Not Checked Out Yet'
            total_hours = 'N/A'

        attendance_data.append({
            'check_in_time': check_in_time,
            'check_out_time': check_out_time,
            'total_hours': total_hours,
        })

    return Response({'logs': attendance_data}, status=status.HTTP_200_OK)


@api_view(['POST'])
def detect_face(request):
    if 'image' not in request.FILES:
        print("[DEBUG] No Image Provided")
        return JsonResponse({'error': 'No image provided'}, status=400)

    try:
        # Get the uploaded image
        image_file = request.FILES['image']
        img = Image.open(image_file).convert('RGB')

        # Resize the image
        original_width, original_height = img.width, img.height
        resized_width, resized_height = 360, 360
        img_resize = img.resize((resized_width, resized_height))

        # Convert image to NumPy array
        img_array = np.array(img_resize)

        # Detect faces using DeepFace
        try:
            detections = DeepFace.extract_faces(
                img_array, detector_backend="yolov8", align=True
            )
            print(f"[DEBUG] Detections:", detections)

            if not detections:
                return JsonResponse({
                    'face_detected': False,
                    'num_faces': 0,
                    'faces': [],
                })

            # Initialize face data and save directory
            faces = []
            save_directory = os.path.join(settings.MEDIA_ROOT, "images")
            os.makedirs(save_directory, exist_ok=True)

            # Create a drawable object for the resized image
            draw = ImageDraw.Draw(img_resize)

            for i, detection in enumerate(detections):
                bbox = detection.get('facial_area', None)  # Use DeepFace's bounding box info
                if bbox:
                    # Scale bounding box coordinates back to original dimensions
                    x = int(bbox['x'] * original_width / resized_width)
                    y = int(bbox['y'] * original_height / resized_height)
                    w = int(bbox['w'] * original_width / resized_width)
                    h = int(bbox['h'] * original_height / resized_height)

                    # Crop face from the original image
                    cropped_img = img.crop((x, y, x + w, y + h))

                    # Generate a unique filename using uuid
                    unique_filename = f"face_{uuid.uuid4().hex}.jpg"
                    cropped_face_path = os.path.join(save_directory, unique_filename)
                    cropped_img.save(cropped_face_path)

                    # Append face data for response
                    faces.append({'path': f"media/images/{unique_filename}", 'bbox': {'x': x, 'y': y, 'width': w, 'height': h}})
                    print(f"[DEBUG] Faces:", faces[i])

                    # Draw bounding box on the resized image (use resized dimensions)
                    draw.rectangle(
                        [(bbox['x'], bbox['y']), (bbox['x'] + bbox['w'], bbox['y'] + bbox['h'])],
                        outline="red",
                        width=3
                    )

            # Save the image with bounding boxes
            annotated_image_filename = f"annotated_image_{uuid.uuid4().hex}.jpg"
            annotated_image_path = os.path.join(save_directory, annotated_image_filename)
            img_resize.save(annotated_image_path)

            return JsonResponse({
                'face_detected': True,
                'num_faces': len(faces),
                'faces': faces,
                'annotated_image': f"media/images/{annotated_image_filename}",
                'cropped_image': f"media/images/{unique_filename}"
            })

        except Exception as detection_error:
            print(f"DeepFace detection error: {str(detection_error)}")
            return JsonResponse({'error': f'Face detection error: {str(detection_error)}'}, status=500)

    except Exception as e:
        print("Error during face detection:", str(e))
        return JsonResponse({'error': f'Error during face detection: {str(e)}'}, status=500)



# Initialize the MTCNN detector once to avoid reloading on every request
detector = MTCNN()
@api_view(['POST'])
def verify_face(request):
    if 'image' not in request.FILES:
        print(f"[DEBUG] No Image Provided")
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

        reference_image_path = os.path.join(settings.MEDIA_ROOT, str(user.faceImage))  # Adjust path if needed
        print(f"[DEBUG] reference_image_path: {reference_image_path}")

        # 3. Face Verification Using DeepFace
        verification_results = []
        for face_path in cropped_face_paths:
            try:
# result = DeepFace.verify(img1_path, img2_path, model_name="VGG-Face", detector_backend="opencv", distance_metric="cosine", enforce_detection=True, align=True, normalization="base")

                result = DeepFace.verify(
                    img1_path=face_path, # Crop Image
                    img2_path=reference_image_path, # User Face Image in Database
                    model_name="Facenet",  # or "VGG-Face"
                    enforce_detection=False
                )
                 # Extract the distance or similarity score
                distance = result['distance']  # The smaller the distance, the more similar the faces
                
                # Set the threshold to 0.3  , distance need to < threshold
                threshold = 0.4

                # Check if faces are verified based on the threshold
                if distance < threshold:
                    verification_results.append({
                    'face_path': face_path,
                    'verified': True,
                    'distance': result['distance'],
                    'threshold': result['threshold'],
                    'similarity': 1 - result['distance'],  # Calculate similarity
                })                    
                else:
                    verification_results.append({
                    'face_path': face_path,
                    'verified': False,
                    'distance': result['distance'],
                    'threshold': result['threshold'],
                    'similarity': 1 - result['distance'],  # Calculate similarity
                }) 
            
                    
                # verification_results.append({
                #     'face_path': face_path,
                #     'verified': result['verified'],
                #     'distance': result['distance'],
                #     'threshold': result['threshold'],
                #     'similarity': 1 - result['distance'],  # Calculate similarity
                # })  
                print(f"[DEBUG] Result: {verification_results}")
                detected_image_path = "/media/images/detected_faces.jpg"
                print(f"[DEBUG] detected_image_path: {detected_image_path}")



            except Exception as e:
                print(f"Error verifying face {face_path} against reference: {e}")
                verification_results.append({'face_path': face_path, 'error': str(e)})

        if verification_results and any(result['verified'] for result in verification_results):
            # If at least one face was verified, log attendance
            # Get today's date and time
            now = datetime.now()
            today = now.date()

            # Define valid check-in and check-out times
            check_in_start = time(9, 0) 
            check_in_end = time(11, 0)  
            check_out_start = time(18, 0)  
            check_out_end = time(23, 59)    
            
            attendance, created = AttendanceLog.objects.get_or_create(employee=user, date=today)
            
            # Check if it's within check-in time range
            if not AttendanceLog.objects.filter(employee=user, date=today).exists():
                # Attendance not recorded yet, allow check-in
                if check_in_start <= now.time() <= check_in_end:
                    attendance = AttendanceLog.objects.create(employee=user, date=today, check_in_time=now)
                    message = "Check-in successful"
                else:
                    message = f"Check-in is only allowed between {check_in_start} and {check_in_end}."
            else:
                # Attendance already exists, check if it's check-out time
                attendance = AttendanceLog.objects.get(employee=user, date=today)

                if attendance.check_out_time is None:  # If not checked out
                    if check_out_start <= now.time() <= check_out_end:
                        attendance.check_out_time = now
                        attendance.save()
                        message = "Check-out successful"
                    else:
                        message = f"Check-out is only allowed between {check_out_start} and {check_out_end}."
                else:
                    message = "Attendance already logged for today"

            print(f"[DEBUG] Attendance: {message}")

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

#     except Exception as e:
#         print("[ERROR] General Error:", e)
#         return Response({"error": "An error occurred while processing the image.", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
