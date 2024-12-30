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
from django.contrib.auth.hashers import check_password, make_password
from rest_framework.parsers import MultiPartParser
from .serializers import EmployeeSerializer, AttendanceSerializer
from base.models import Employee, CheckInCheckOutTime, AttendanceLog
from deepface import DeepFace
from datetime import datetime, time, date
import uuid
import concurrent.futures

@api_view(['GET'])
def get_check_in_status(request, user_id):
    try:
        today = date.today()
        attendance_log = AttendanceLog.objects.filter(employee_id=user_id, date=today).first()
        if attendance_log:
            if attendance_log.check_in_time and attendance_log.check_out_time:
                return Response({'checked_in': False, 'checked_out': True}, status=status.HTTP_200_OK)
            elif attendance_log.check_in_time:
                return Response({'checked_in': True, 'checked_out': False}, status=status.HTTP_200_OK)
        return Response({'checked_in': False, 'checked_out': False}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': f'An error occurred: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
@api_view(['GET'])
def get_user_role(request, user_id):
    try:
        user = Employee.objects.get(id=user_id)
        return Response({'role': user.role}, status=status.HTTP_200_OK)
    except Employee.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': f'An error occurred: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def get_times(request):
    try:
        check_in_check_out_time = CheckInCheckOutTime.objects.first()
        if not check_in_check_out_time:
            return Response({'error': 'No times set'}, status=status.HTTP_404_NOT_FOUND)

        data = {
            'check_in_start': check_in_check_out_time.check_in_start_time.strftime('%H:%M'),
            'check_in_end': check_in_check_out_time.check_in_end_time.strftime('%H:%M'),
            'check_out_start': check_in_check_out_time.check_out_start_time.strftime('%H:%M'),
            'check_out_end': check_in_check_out_time.check_out_end_time.strftime('%H:%M'),
        }
        return Response(data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': f'An error occurred: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def update_times(request):
    check_in_start = request.data.get('check_in_start')
    check_in_end = request.data.get('check_in_end')
    check_out_start = request.data.get('check_out_start')
    check_out_end = request.data.get('check_out_end')

    print(f"[DEBUG] Received data: check_in_start={check_in_start}, check_in_end={check_in_end}, check_out_start={check_out_start}, check_out_end={check_out_end}")


    if not all([check_in_start, check_in_end, check_out_start, check_out_end]):
        return Response({'error': 'All time fields are required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        # Convert strings to time objects
        check_in_start_time = datetime.strptime(check_in_start, '%H:%M').time()
        check_in_end_time = datetime.strptime(check_in_end, '%H:%M').time()
        check_out_start_time = datetime.strptime(check_out_start, '%H:%M').time()
        check_out_end_time = datetime.strptime(check_out_end, '%H:%M').time()

        # Get or create the CheckInCheckOutTime instance
        check_in_check_out_time, created = CheckInCheckOutTime.objects.get_or_create(id=1)
        check_in_check_out_time.check_in_start_time = check_in_start_time
        check_in_check_out_time.check_in_end_time = check_in_end_time
        check_in_check_out_time.check_out_start_time = check_out_start_time
        check_in_check_out_time.check_out_end_time = check_out_end_time
        check_in_check_out_time.save()

        return Response({'success': 'Times updated successfully'}, status=status.HTTP_200_OK)
    except ValueError:
        return Response({'error': 'Invalid time format, use HH:MM'}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({'error': f'An error occurred: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def update_face_image(request):
    user_id = request.query_params.get('user_id')
    if not user_id:
        return Response({'error': 'User ID is required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        employee = Employee.objects.get(id=user_id)
    except Employee.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

    if 'faceImage' not in request.FILES:
        return Response({'error': 'No image provided'}, status=status.HTTP_400_BAD_REQUEST)

    face_image = request.FILES['faceImage']
    print(f"[DEBUG] face_image: {face_image}")
    employee.faceImage = face_image
    employee.save()

    return Response({'success': 'Face image updated successfully', 'faceImage': employee.faceImage.url}, status=status.HTTP_200_OK)


@api_view(['POST'])
def changePassword(request):
    user_id = request.data.get('user_id')
    current_password = request.data.get('current_password')
    new_password = request.data.get('new_password')

    if not user_id or not current_password or not new_password:
        return Response({'error': 'All fields are required'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        employee = Employee.objects.get(id=user_id)
        print(f"[DEBUG] employee: {employee}")
        print(f"[DEBUG] current_password: {current_password}")
        print(f"[DEBUG] new_password: {new_password}")
        if check_password(current_password, employee.password):
            employee.password = make_password(new_password)
            employee.save()
            return Response({'success': 'Password changed successfully'}, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'Current password is incorrect'}, status=status.HTTP_400_BAD_REQUEST)
    except Employee.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        print(f"[DEBUG] image: {str(e)}")
        return Response({'error': f'An error occurred: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

 
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
            if check_password(password, employee.password):
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

@api_view(['POST'])
def verify_face(request):
    if 'image' not in request.FILES:
        return Response({'error': 'No image provided'}, status=400)

    try:
        # 1. Process the Captured Image
        image_file = request.FILES['image']
        img = Image.open(image_file).convert('RGB')

        # Resize image for consistency
        img_resized = img.resize((160, 160))  # Smaller size for faster processing
        img_array = np.array(img_resized)

        # Detect faces using DeepFace.extract_faces
        detections = DeepFace.extract_faces(img_path=img_array, enforce_detection=False)

        if len(detections) == 0:
            return Response({'faces_detected': 0})

        for detection in detections:
            region = detection["facial_area"]
            x, y, width, height = region['x'], region['y'], region['w'], region['h']

            # Crop face from the resized image
            cropped_face = img_resized.crop((x, y, x + width, y + height))
            cropped_face_path = os.path.join(settings.MEDIA_ROOT, "images", "cropped_face.jpg")
            cropped_face.save(cropped_face_path)

            # 2. Retrieve the Reference Image from Database
            user_id = request.POST.get('user_id')
            if not user_id:
                return Response({'error': 'user_id is required'}, status=status.HTTP_400_BAD_REQUEST)

            user = Employee.objects.filter(id=user_id).first()
            if not user:
                return Response({'error': 'User not found'}, status=404)

            if not user.faceImage:
                return Response({'error': 'Face image not found for this user'}, status=404)

            reference_image_path = os.path.join(settings.MEDIA_ROOT, str(user.faceImage))

            # 3. Face Verification Using DeepFace
            def verify_face():
                try:
                    result = DeepFace.verify(
                        img1_path=cropped_face_path,  # Cropped Image
                        img2_path=reference_image_path,  # User Face Image in Database
                        model_name="Facenet",  # or "VGG-Face"
                        enforce_detection=False
                    )
                    return result
                except Exception as e:
                    return {'error': str(e)}

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(verify_face)
                result = future.result()

            if 'error' in result:
                return Response({'error': result['error']}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # Extract the distance or similarity score
            distance = result['distance']  # The smaller the distance, the more similar the faces

            # Set the threshold to 0.3, distance need to < threshold
            threshold = 0.4
            detected_image_path = "/media/images/detected_faces.jpg"

            # Check if faces are verified based on the threshold
            if distance < threshold:
                verification_results = {
                    'face_path': cropped_face_path,
                    'verified': True,
                    'distance': result['distance'],
                    'threshold': threshold,
                    'similarity': 1 - result['distance'],  # Calculate similarity
                }

                # Log attendance
                now = datetime.now()
                today = now.date()

                try:
                    check_in_check_out_time = CheckInCheckOutTime.objects.first()
                    check_in_start = check_in_check_out_time.check_in_start_time
                    check_in_end = check_in_check_out_time.check_in_end_time
                    check_out_start = check_in_check_out_time.check_out_start_time
                    check_out_end = check_in_check_out_time.check_out_end_time
                except CheckInCheckOutTime.DoesNotExist:
                    return Response({'error': 'Check-in/check-out times not set'}, status=404)

                attendance, created = AttendanceLog.objects.get_or_create(employee=user, date=today)

                if not created:
                    if attendance.check_out_time is None:
                        if check_out_start <= now.time() <= check_out_end:
                            attendance.check_out_time = now
                            attendance.save()
                            message = "Check-out successful"
                        else:
                            message = f"Check-out is only allowed between {check_out_start} and {check_out_end}."
                    else:
                        message = "Attendance already logged for today"
                else:
                    if check_in_start <= now.time() <= check_in_end:
                        attendance.check_in_time = now
                        attendance.save()
                        message = "Check-in successful"
                    else:
                        attendance.delete()  # Remove the created record if check-in is not allowed
                        message = f"Check-in is only allowed between {check_in_start} and {check_in_end}."

                return Response({
                    'message': message,
                    'faces_detected': 1,
                    'verification_results': verification_results,
                    'detected_image_path': detected_image_path,
                    'check_in_time': attendance.check_in_time.strftime('%H:%M:%S') if attendance.check_in_time else 'N/A',
                    'check_out_time': attendance.check_out_time.strftime('%H:%M:%S') if attendance.check_out_time else 'N/A',
                })

        return Response({'message': "Face verification failed", 'faces_detected': len(detections)})

    except Exception as e:
        return Response({'error': f'Error during face verification: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
