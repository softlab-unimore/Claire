from django import forms
from django.contrib.auth.models import User
from .models import UserProfile, Group, Activity

import uuid

class LoginForm(forms.Form):
    username = forms.CharField(max_length=100)
    password = forms.CharField(widget=forms.PasswordInput)
    
    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get('username')
        password = cleaned_data.get('password')
        
        if not username or not password:
            raise forms.ValidationError("Both fields are required.")
        return cleaned_data

class RegistrationForm(forms.ModelForm):
    CHOICES = {
       "1": "student",
       "2": "teacher"
    }
    
    username = forms.CharField(
        max_length=150,
        error_messages={
            'required': '',
            'max_length': '',
            'invalid': ''
        }
    )
    role = forms.ChoiceField(widget=forms.RadioSelect, choices=CHOICES)
    password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)
    
    class Meta:
       model = User
       fields = ['email', 'username']

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        username = cleaned_data.get('username')
        role = cleaned_data.get('role')
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        
        if password != confirm_password:
            raise forms.ValidationError("Passwords do not match.")
        if not email or not username or not role or not password or not confirm_password:
            raise forms.ValidationError("All fields are required.")
        return cleaned_data

class CreateClass(forms.Form):
    class_name = forms.CharField(max_length=100)
    share_link = forms.CharField(max_length=256, widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.group_id = None
        if len(args) > 0 and 'group_id' in args[0].keys():
            self.group_id = args[0]['group_id']
            self.fields["class_name"].initial = Group.objects.get(id=self.group_id).name
            self.fields["share_link"].initial = Group.objects.get(id=self.group_id).share_link
            self.fields["class_name"].required = False
            self.fields["share_link"].required = False

            args[0]._mutable = True
            args[0]['class_name'] = self.fields["class_name"].initial
            args[0]['share_link'] = self.fields["share_link"].initial
            args[0]._mutable = False

            self.fields['share_link'].widget.attrs['readonly'] = True
        else:
            generated_id = uuid.uuid1().hex
            self.fields['share_link'].initial = generated_id

    def clean(self):
        cleaned_data = super().clean()
        class_name = cleaned_data.get('class_name')
        share_link = cleaned_data.get('share_link')

        if self.group_id is not None:
           class_name = self.fields["class_name"].initial
           share_link = self.fields["share_link"].initial
           cleaned_data['share_link'] = share_link
           cleaned_data['class_name'] = share_link
        else:
           self.group_id = ""

        if not class_name or class_name == "" or self.group_id is None:
            raise forms.ValidationError("A class name is required")

        return cleaned_data

class JoinClass(forms.Form):
    share_link = forms.CharField(max_length=256)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.group_id = None
        if len(args) > 0 and 'group_id' in args[0].keys():
            self.group_id = args[0]['group_id']
            self.fields["share_link"].initial = Group.objects.get(id=self.group_id).share_link
            self.fields["share_link"].required = False

            args[0]._mutable = True
            args[0]['share_link'] = self.fields["share_link"].initial
            args[0]._mutable = False

            self.fields['share_link'].widget.attrs['readonly'] = True

    def clean(self):
        cleaned_data = super().clean()
        share_link = cleaned_data.get('share_link')
        if self.group_id is not None:
           share_link = self.fields["share_link"].initial
           cleaned_data['share_link'] = share_link
        else:
           self.group_id = ""

        if not share_link or share_link == "" or self.group_id is None:
            raise forms.ValidationError("A class name is required")
        return cleaned_data

class GetActivityForm(forms.Form):
   name = forms.CharField(max_length=256)
   description = forms.CharField()
   text = forms.CharField()

   phases = forms.FileField()
   criteria = forms.FileField()
   interaction = forms.FileField()
   logic = forms.FileField()

   def __init__(self, *args, **kwargs):
       super().__init__(*args, **kwargs)

       self.activity_id = None
       if len(args) > 0 and 'activity_id' in args[0].keys():
          try:
              self.activity_id = args[0]['activity_id']
              self.fields["name"].initial = Activity.objects.get(id=self.activity_id).name
              self.fields["description"].initial = Activity.objects.get(id=self.activity_id).description
              self.fields["text"].initial = Activity.objects.get(id=self.activity_id).text

              args[0]._mutable = True
              args[0]['name'] = self.fields["name"].initial
              args[0]['description'] = self.fields["description"].initial
              args[0]['text'] = self.fields["text"].initial
              args[0]._mutable = False
          except:
              pass

   def clean(self):
       cleaned_data = super().clean()
       name = cleaned_data.get('name')
       description = cleaned_data.get('description')
       text = cleaned_data.get('text')
       
       if not name or not description or not text:
           raise forms.ValidationError("All fields are required.")
       return cleaned_data

class PostActivityForm(forms.Form):
   name = forms.CharField(max_length=256)
   description = forms.CharField()
   text = forms.CharField()

   phases = forms.FileField()
   criteria = forms.FileField()
   interaction = forms.FileField()
   logic = forms.FileField()

   def clean(self):
       cleaned_data = super().clean()
       required_files = ['phases', 'criteria', 'interaction', 'logic']

       name = cleaned_data.get('name')
       description = cleaned_data.get('description')
       text = cleaned_data.get('text')
       
       if not name or not description or not text:
           raise forms.ValidationError("All fields are required.")

       for field in required_files:
           file = cleaned_data.get(field)
           if not file:
               raise forms.ValidationError("no files All fields are required.")
           if not file.name.endswith('.csv') or file.content_type != 'text/csv':
               raise forms.ValidationError(f"All uploaded files must be CSV files.")

       return cleaned_data
