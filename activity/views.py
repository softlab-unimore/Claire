from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseForbidden
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from .forms import LoginForm, RegistrationForm, CreateClass, JoinClass, GetActivityForm, PostActivityForm
from .models import Group, Activity, Dataset, UserActivity
from .methods import openaimodel
from .agent_from_csv import agent

from django.contrib.auth.decorators import login_required

from .prompts.prompts_csv.system_prompt import system_prompt

from django.http import HttpResponse
import json

import io

def get_login(request):
   if request.method == "POST":
      form = LoginForm(request.POST)
      if form.is_valid():
         username = form.cleaned_data["username"]
         password = form.cleaned_data["password"]
         user = authenticate(request, username=username, password=password)
         if user is not None:
            login(request, user)
            return redirect(index)
         else:
            form.add_error(None, "Invalid credentials")
   else:
      form = LoginForm()

   return render(request, "activity/login.html", {"form": form})

def register(request):
   if request.method == "POST":
      form = RegistrationForm(request.POST)
      if form.is_valid():
         username = form.cleaned_data["username"]
         password = form.cleaned_data["password"]
         role = form.cleaned_data["role"]
         email = form.cleaned_data["email"]

         user = User.objects.create_user(username=username, password=password, email=email)
         user.userprofile.role = role
         user.userprofile.save()

         login(request, user)
         return redirect(index)
      else:
         form.add_error(None, "Every field must be correctly filled")
   else:
      form = RegistrationForm()

   return render(request, "activity/register.html", {"form": form})

@login_required
def logout_request(request):
   logout(request)
   return redirect(get_login)

@login_required
def create_class(request):
   error = False
   if request.method == "POST":
         if request.user.userprofile.role == "2":
            form = CreateClass(request.POST)
         else:
            form = JoinClass(request.POST)

         if form.is_valid():
            share_link = form.cleaned_data["share_link"]
            if request.user.userprofile.role == "2":
               class_name = form.cleaned_data["class_name"]
               if share_link in [group.share_link for group in Group.objects.filter(userprofiles=request.user.userprofile)]:
                  group = Group.objects.get(userprofiles=request.user.userprofile, share_link=share_link)
                  group.name = class_name
                  group.save()
               elif class_name in [group.name for group in Group.objects.filter(userprofiles=request.user.userprofile)]:
                  error = True
                  form.add_error(None, f"You already have a class named {class_name}. Please choose another name")
                  group = None
               else:
                  group = Group.objects.create(name=class_name, share_link=share_link)
            else:
               group = Group.objects.get(share_link=share_link)

            if group == None:
               if not error:
                  form.add_error(None, "Wrong class link. Insert the correct class link.")
            else:
               group.userprofiles.add(request.user.userprofile)
               return redirect(index)
         else:
            form.add_error(None, "Every field must be correctly filled")
         context = {"form": form, "role": request.user.userprofile.role}
   elif request.method == "GET":
      if "group_id" in request.GET.keys():
         if request.user.userprofile.role == "2":
            form = CreateClass(request.GET)
         else:
            form = JoinClass(request.GET)

         users = [(userprofile.user.username, "Studente" if userprofile.role == "1" else "Insegnante") for userprofile in Group.objects.get(id=request.GET["group_id"]).userprofiles.all()]
         users = sorted(users, key=lambda x: x[1] == "Insegnante", reverse=True)
         context = {"form": form, "role": request.user.userprofile.role, "group_id": request.GET["group_id"], "users": users}
      else:
         if request.user.userprofile.role == "2":
            form = CreateClass()
         else:
            form = JoinClass()
         context = {"form": form, "role": request.user.userprofile.role}
   else:
      if request.user.userprofile.role == "2":
         form = CreateClass()
      else:
         form = JoinClass()
      context = {"form": form, "role": request.user.userprofile.role}

   return render(request, "activity/members.html", context)

@login_required
def index(request):
    if "messages" in request.session:
        del request.session["messages"]
        del request.session["total_messages"]
        request.session.modified = True
    if "stage" in request.session:
        del request.session["stage"]
        request.session.modified = True
    groups = Group.objects.filter(userprofiles=request.user.userprofile)
    return render(request, "activity/index.html", {"role": request.user.userprofile.role, "groups": groups})

@login_required
def get_activity_page(request):
   if request.method != "POST":
      return redirect(index)
   group_id = request.POST.get('group_id')
   if group_id:
      activities = Activity.objects.filter(group_id=group_id)
   else:
      activities = []
   return render(request, "activity/activity.html", {"role": request.user.userprofile.role, "activities": activities, "group_id": group_id})

@login_required
def get_members(request):
   return render(request, "activity/members.html", {"role": request.user.userprofile.role})

@login_required
def get_new_activity(request):
    if request.user.userprofile.role != "2":
       return HttpResponseForbidden("You are not allowed to edit this activity.")
    if request.method == "POST":
        form = PostActivityForm(request.POST, request.FILES)
        if form.is_valid():
            name = form.cleaned_data["name"]
            description = form.cleaned_data["description"]
            text = form.cleaned_data["text"]

            phases = form.cleaned_data["phases"].read() # io.BytesIO(request.FILES['phases'].read())
            criteria = form.cleaned_data["criteria"].read() # io.BytesIO(request.FILES['criteria'].read())
            interaction = form.cleaned_data["interaction"].read() # io.BytesIO(request.FILES['interaction'].read())
            logic = form.cleaned_data["logic"].read() # io.BytesIO(request.FILES['logic'].read())

            activity_id = request.POST.get("activity_id", None)
            group_id = request.POST.get("group_id")

            if activity_id:
                activity = get_object_or_404(Activity, id=activity_id)
                if request.user.userprofile not in activity.group_id.userprofiles.all():
                    return HttpResponseForbidden("You are not allowed to edit this activity.")

                dataset = activity.dataset

                activity.name = name
                activity.description = description
                activity.text = text
                dataset.phases = phases
                dataset.criteria = criteria
                dataset.interaction = interaction
                dataset.logic = logic

                activity.save()
                dataset.save()
            else:
                group = get_object_or_404(Group, id=group_id)

                if request.user.userprofile not in group.userprofiles.all():
                    return HttpResponseForbidden("You are not allowed to create activities for this group.")

                activity = Activity.objects.create(name=name, description=description, text=text, group_id=group)
                Dataset.objects.create(
                    activity=activity,
                    phases=phases,
                    criteria=criteria,
                    interaction=interaction,
                    logic=logic
                )

            return redirect(index)

        context = {"form": form, "role": request.user.userprofile.role, "group_id": request.POST["group_id"]}
    else:
        if "activity_id" in request.GET:
           form = GetActivityForm(request.GET)
           context = {"form": form, "role": request.user.userprofile.role, "group_id": request.GET["group_id"], "activity_id": request.GET["activity_id"]}
        else:
           form = GetActivityForm()
           context = {"form": form, "role": request.user.userprofile.role, "group_id": request.GET["group_id"]}

    return render(request, "activity/new_activity.html", context)

@login_required
def get_chat(request):
    if request.method == "GET":
        activity = get_object_or_404(Activity, id=request.GET["activity_id"])
    elif request.method == "POST":
        activity = get_object_or_404(Activity, id=request.POST["activity_id"])

    if request.method == "GET":
        if "stage" not in request.session:
            request.session["stage"] = 1
            request.session["num_interactions"] = 0

        if "messages" not in request.session or len(request.session["messages"]) == 0:
            system_message = {
                "text": system_prompt,
                "sender": "system",
            }

            request.session["messages"], request.session["total_messages"] = agent.apply_phase(request.session["stage"], [system_message], [system_message], activity=activity)

        additional_context = {"group_id": request.GET["group_id"], "activity_id": request.GET["activity_id"]}
    elif request.method == "POST":
        if "stage" not in request.session:
            request.session["stage"] = 1
            request.session["num_interactions"] = 0

        if agent.is_activity_finished(request.session["stage"], activity):
            messages_to_send = [{
                "text": message["text"].replace("Bot: ", "").replace("User: ", ""),
                "sender": message["sender"],
            } for message in request.session["messages"] if message["sender"] != "system"]
            additional_context = {}
            blocked = True

            useractivity = get_object_or_404(UserActivity, user_id=request.user.id, activity_id=activity.id)
            useractivity.status = useractivity.Status.DONE
            useractivity.save()

            return render(request, "activity/chat.html",
                   {"role": request.user.userprofile.role, "messages": messages_to_send, "blocked": blocked,
                    "stage": request.session["stage"]} | additional_context)

        previous_interaction = request.session.get("previous_interaction", None)

        request.session["messages"].append({
            "text": request.POST["message"],
            "sender": "user",
        })
        request.session["total_messages"].append({
            "text": request.POST["message"],
            "sender": "user",
        })
        request.session.modified = True

        request.session["messages"], request.session["total_messages"], criteria = agent.apply_criteria(request.session["stage"], request.session["messages"], request.session["total_messages"], activity=activity)
        next_interaction = agent.apply_logic(request.session["stage"], criteria, activity, previous_interaction)
        if next_interaction == "next" or agent.are_interactions_too_many(request.session["num_interactions"]):
            request.session["stage"] += 1
            request.session["previous_interaction"] = None
            if agent.is_activity_finished(request.session["stage"], activity):
                request.session["messages"].append({
                    "text": "Complimenti! Hai terminato l'attività!",
                    "sender": "bot",
                })
                request.session["total_messages"].append({
                    "text": "Complimenti! Hai terminato l'attività!",
                    "sender": "bot",
                })
            else:
                request.session["messages"], request.session["total_messages"] = agent.apply_phase(request.session["stage"], request.session["messages"], request.session["total_messages"], activity=activity)
            request.session.modified = True
            request.session["num_interactions"] = 0
        else:
            request.session["messages"], request.session["total_messages"], previous_interaction = agent.apply_interaction(request.session["stage"], request.session["messages"], request.session["total_messages"], next_interaction, activity)
            request.session["previous_interaction"] = previous_interaction
            request.session["num_interactions"] += 1

        request.session.modified = True

        additional_context = {"group_id": request.POST["group_id"], "activity_id": request.POST["activity_id"]}
    else:
        additional_context = {}

    if agent.is_activity_finished(request.session["stage"], activity):
        blocked = True
    else:
        blocked = False

    messages_to_send = [{
        "text": message["text"].replace("Bot: ", "").replace("User: ", ""),
        "sender": message["sender"],
    } for message in request.session["messages"] if message["sender"] != "system"]

    print(request.session["total_messages"])

    return render(request, "activity/chat.html", {"role": request.user.userprofile.role, "messages": messages_to_send, "blocked": blocked, "stage": request.session["stage"]} | additional_context)

@login_required
def download_total_messages(request):
    total_messages = request.session.get("total_messages", [])

    content = json.dumps(total_messages, indent=2, ensure_ascii=False)

    response = HttpResponse(content, content_type='application/json')
    response['Content-Disposition'] = 'attachment; filename="total_messages.json"'
    return response