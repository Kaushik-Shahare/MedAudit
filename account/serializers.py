from django.contrib.auth import authenticate, get_user_model
from rest_framework import serializers
from .models import UserProfile, Address, EmergencyContact, Insurance

User = get_user_model()

class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = ['id', 'street', 'area', 'city', 'state', 'pincode', 'country', 'is_primary']
        read_only_fields = ['user']
        extra_kwargs = {
            'street': {'required': False},
            'area': {'required': False},
            'city': {'required': False},
            'state': {'required': False}, 
            'pincode': {'required': False},
            'country': {'required': False},
            'is_primary': {'required': False},
        }
        
    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

class EmergencyContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmergencyContact
        fields = ['id', 'name', 'relation', 'phone_number']
        read_only_fields = ['user']
        extra_kwargs = {
            'name': {'required': False},
            'relation': {'required': False},
            'phone_number': {'required': False},
        }
        
    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

class InsuranceSerializer(serializers.ModelSerializer):
    valid_till = serializers.DateField(required=False, format='%Y-%m-%d')
    
    class Meta:
        model = Insurance
        fields = ['id', 'provider', 'policy_number', 'valid_till']
        read_only_fields = ['user']
        extra_kwargs = {
            'provider': {'required': False},
            'policy_number': {'required': False},
        }
        
    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

class UserProfileSerializer(serializers.ModelSerializer):
    patient_id = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    user_type = serializers.SerializerMethodField()
    age = serializers.SerializerMethodField()
    address = AddressSerializer(required=False, write_only=True)
    emergency_contact = EmergencyContactSerializer(required=False, write_only=True) 
    insurance = InsuranceSerializer(required=False, write_only=True)
    primary_physician = serializers.DictField(required=False, write_only=True)
    location = serializers.CharField(required=False)
    
    # Read-only fields for nested data (separate from write fields)
    address_data = serializers.SerializerMethodField(read_only=True)
    emergency_contact_data = serializers.SerializerMethodField(read_only=True)
    insurance_data = serializers.SerializerMethodField(read_only=True)
    primary_physician_data = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = UserProfile
        fields = [
            'patient_id', 'name', 'gender', 'date_of_birth', 'age', 'email',
            'phone_number', 'location', 'address_data', 'blood_group', 'height_cm', 
            'weight_kg', 'marital_status', 'emergency_contact_data', 'insurance_data',
            'allergies', 'chronic_conditions', 'current_medications', 'last_visit',
            'primary_physician_data', 'vaccination_status', 'user_type',
            # Write fields
            'address', 'emergency_contact', 'insurance', 'primary_physician'
        ]
        extra_kwargs = {
            'name': {'required': False},
            'phone_number': {'required': False},
            'date_of_birth': {'required': False},
            'gender': {'required': False},
            'blood_group': {'required': False},
            'height_cm': {'required': False},
            'weight_kg': {'required': False},
            'marital_status': {'required': False},
            'allergies': {'required': False},
            'chronic_conditions': {'required': False},
            'current_medications': {'required': False},
            'last_visit': {'required': False},
            'vaccination_status': {'required': False},
        }
    
    def get_patient_id(self, obj):
        try:
            return obj.user.id
        except:
            return None
    
    def get_email(self, obj):
        try:
            return obj.user.email
        except:
            return None
    
    def get_age(self, obj):
        try:
            if not obj.date_of_birth:
                return None
                
            from datetime import date
            today = date.today()
            born = obj.date_of_birth
            age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
            return age
        except:
            return None

    def get_user_type(self, obj):
        try:
            return obj.user.user_type.name if obj.user.user_type else None
        except:
            return None
            
    def get_address_data(self, obj):
        try:
            address = obj.user.addresses.filter(is_primary=True).first()
            if address:
                return {
                    "id": address.id,
                    "street": address.street or "",
                    "area": address.area or "",
                    "city": address.city or "",
                    "state": address.state or "",
                    "pincode": address.pincode or "",
                    "country": address.country or "",
                    "is_primary": address.is_primary
                }
            return None
        except:
            return None
        
    def get_emergency_contact_data(self, obj):
        try:
            contact = obj.user.emergency_contacts.first()
            if contact:
                return {
                    "id": contact.id,
                    "name": contact.name or "",
                    "relation": contact.relation or "",
                    "phone_number": contact.phone_number or ""
                }
            return None
        except:
            return None
        
    def get_insurance_data(self, obj):
        try:
            insurance = obj.user.insurance_policies.first()
            if insurance:
                return {
                    "id": insurance.id,
                    "provider": insurance.provider or "",
                    "policy_number": insurance.policy_number or "",
                    "valid_till": insurance.valid_till
                }
            return None
        except:
            return None
        
    def get_primary_physician_data(self, obj):
        try:
            # Check if we have physician data in the department or hospital fields
            if not (obj.department or obj.hospital):
                return None
                
            physician_data = {}
            
            # For the name, use a default if we don't have a real physician relation
            physician_data["name"] = "Dr. Unknown"
            
            # If we have a primary_physician relationship, use that data
            if obj.primary_physician:
                if obj.primary_physician.name:
                    physician_name = obj.primary_physician.name
                    if not physician_name.startswith('Dr. '):
                        physician_name = f"Dr. {physician_name}"
                    physician_data["name"] = physician_name
            
            # Get department
            if obj.department:
                physician_data["department"] = obj.department
                
            # Get hospital
            if obj.hospital:
                physician_data["hospital"] = obj.hospital
                
            return physician_data
        except:
            return None
    
    def validate(self, attrs):
        """
        Custom validation to handle nested data and prevent errors
        """
        # Make sure none of these fields cause validation errors
        if 'vaccination_status' in attrs and not isinstance(attrs['vaccination_status'], dict):
            attrs['vaccination_status'] = {}
            
        if 'allergies' in attrs and not isinstance(attrs['allergies'], list):
            attrs['allergies'] = []
            
        if 'chronic_conditions' in attrs and not isinstance(attrs['chronic_conditions'], list):
            attrs['chronic_conditions'] = []
            
        if 'current_medications' in attrs and not isinstance(attrs['current_medications'], list):
            attrs['current_medications'] = []
            
        if 'address' in attrs:
            # Ensure all fields in address are strings
            for field in ['street', 'area', 'city', 'state', 'pincode', 'country']:
                if field in attrs['address'] and attrs['address'][field] is None:
                    attrs['address'][field] = ''
        
        if 'emergency_contact' in attrs:
            # Ensure all fields in emergency_contact are strings
            for field in ['name', 'relation', 'phone_number']:
                if field in attrs['emergency_contact'] and attrs['emergency_contact'][field] is None:
                    attrs['emergency_contact'][field] = ''
                    
        if 'insurance' in attrs:
            # Ensure provider and policy_number are strings
            for field in ['provider', 'policy_number']:
                if field in attrs['insurance'] and attrs['insurance'][field] is None:
                    attrs['insurance'][field] = ''
                    
        return attrs
    
    def update(self, instance, validated_data):
        address_data = validated_data.pop('address', None)
        emergency_contact_data = validated_data.pop('emergency_contact', None)
        insurance_data = validated_data.pop('insurance', None)
        primary_physician_data = validated_data.pop('primary_physician', None)
        
        # Update UserProfile fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update or create Address
        if address_data:
            user = instance.user
            Address.objects.update_or_create(
                user=user,
                is_primary=True,
                defaults=address_data
            )
        
        # Update or create EmergencyContact
        if emergency_contact_data:
            user = instance.user
            EmergencyContact.objects.update_or_create(
                user=user,
                defaults=emergency_contact_data
            )
        
        # Update or create Insurance
        if insurance_data:
            valid_till = insurance_data.get('valid_till', None)
            # Convert string date to date object if needed
            if valid_till and isinstance(valid_till, str):
                from datetime import datetime
                try:
                    insurance_data['valid_till'] = datetime.strptime(valid_till, '%Y-%m-%d').date()
                except ValueError:
                    # In case of date format error, remove the field
                    insurance_data.pop('valid_till', None)
                    
            user = instance.user
            Insurance.objects.update_or_create(
                user=user,
                defaults=insurance_data
            )
            
        # Update physician-related fields 
        # We'll store these fields directly in the UserProfile
        if primary_physician_data:
            # These fields already exist in the UserProfile model
            if 'department' in primary_physician_data:
                instance.department = primary_physician_data.get('department')
                
            if 'hospital' in primary_physician_data:
                instance.hospital = primary_physician_data.get('hospital')
                
            # For now, we ignore the physician name since we don't have a field for it
            # If you need to store it, add a field to the UserProfile model
            
            instance.save()
        
        # Return the updated instance
        return instance
        
    def to_representation(self, instance):
        """Customize the output representation for better clarity"""
        ret = super().to_representation(instance)
        
        # Remove write-only fields from output
        for field in ['address', 'emergency_contact', 'insurance', 'primary_physician']:
            if field in ret:
                ret.pop(field)
                
        # Rename the _data fields back to their original names
        if 'address_data' in ret:
            ret['address'] = ret.pop('address_data')
            
        if 'emergency_contact_data' in ret:
            ret['emergency_contact'] = ret.pop('emergency_contact_data')
            
        if 'insurance_data' in ret:
            ret['insurance'] = ret.pop('insurance_data')
            
        if 'primary_physician_data' in ret:
            ret['primary_physician'] = ret.pop('primary_physician_data')
            
        return ret

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    user_type = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('email', 'password', 'user_type')

    def create(self, validated_data):
        user_type = validated_data.pop('user_type', None)
        user = User.objects.create_user(user_type=user_type, **validated_data)
        user.user_stage = 1  # After registration, stage is 1 (profile incomplete)
        user.save()
        # UserProfile will be created by the signal
        return user

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(email=data['email'], password=data['password'])
        if user and user.is_active:
            return user
        raise serializers.ValidationError('Invalid credentials')

class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

class UserDetailSerializer(serializers.ModelSerializer):
    user_type = serializers.SerializerMethodField()
    profile = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'user_type', 'user_stage', 'profile'
        ]
        
    def get_user_type(self, obj):
        return obj.user_type.name if obj.user_type else None
        
    def get_profile(self, obj):
        # Return the patient data format
        try:
            return UserProfileSerializer(obj.profile).data
        except:
            return None