from rest_framework import serializers
from .models import Document, AccessRequest
import os

class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = '__all__'
        
    def validate_file(self, file):
        """
        Validate uploaded file - check file type and size
        """
        # Check file size (100MB limit)
        if file.size > 100 * 1024 * 1024:  # 100MB in bytes
            raise serializers.ValidationError("File size exceeds the maximum limit of 100MB.")
        
        # Get file extension
        file_name = file.name
        ext = os.path.splitext(file_name)[1].lower()
        
        # List of allowed file extensions
        allowed_extensions = [
            # Documents
            '.pdf', '.doc', '.docx', '.rtf', '.txt', '.xls', '.xlsx', '.ppt', '.pptx',
            # Images
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg',
            # Others
            '.csv', '.json', '.xml'
        ]
        
        if ext not in allowed_extensions:
            raise serializers.ValidationError(f"File type {ext} is not supported. Allowed types: {', '.join(allowed_extensions)}")
            
        return file

class AccessRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccessRequest
        fields = '__all__' 