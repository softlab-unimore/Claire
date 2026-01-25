from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseForbidden, StreamingHttpResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from .forms import LoginForm, RegistrationForm, CreateClass, JoinClass, GetActivityForm, PostActivityForm
from .models import Group, Activity, Dataset, UserActivity
from .methods import openaimodel
from .agent_from_csv import AgentFromCsv

from django.contrib.auth.decorators import login_required

from .prompts.prompts_csv.system_prompt import system_prompt

from django.http import HttpResponse
import json

import pandas as pd
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
   class_name = ""

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
               class_name = group.name

            if group == None:
               if not error:
                  form.add_error(None, "Wrong class link. Insert the correct class link.")
            else:
               group.userprofiles.add(request.user.userprofile)
               return redirect(index)
         else:
            form.add_error(None, "Every field must be correctly filled")
         context = {"form": form, "role": request.user.userprofile.role, "group_name": class_name}
   elif request.method == "GET":
      if "group_id" in request.GET.keys():
         if request.user.userprofile.role == "2":
            form = CreateClass(request.GET)
         else:
            form = JoinClass(request.GET)

         group = get_object_or_404(Group, id=request.GET["group_id"])
         class_name = group.name

         users = [(userprofile.user.username, "Studente" if userprofile.role == "1" else "Insegnante") for userprofile in Group.objects.get(id=request.GET["group_id"]).userprofiles.all()]
         users = sorted(users, key=lambda x: x[1] == "Insegnante", reverse=True)
         context = {"form": form, "role": request.user.userprofile.role, "group_id": request.GET["group_id"], "users": users, "group_name": class_name}
      else:
         if request.user.userprofile.role == "2":
            form = CreateClass()
         else:
            form = JoinClass()
         context = {"form": form, "role": request.user.userprofile.role, "group_name": class_name}
   else:
      if request.user.userprofile.role == "2":
         form = CreateClass()
      else:
         form = JoinClass()
      context = {"form": form, "role": request.user.userprofile.role, "group_name": class_name}

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
   group_name = None
   if group_id:
      group = get_object_or_404(Group, id=group_id)
      group_name = group.name
      activities = Activity.objects.filter(group_id=group_id)
   else:
      activities = []
   return render(request, "activity/activity.html", {"role": request.user.userprofile.role, "activities": activities, "group_id": group_id, "group_name": group_name})

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

            activities = Activity.objects.filter(group_id=group_id)
            group = get_object_or_404(Group, id=group_id)
            group_name = group.name
            return render(request, "activity/activity.html",
                          {"role": request.user.userprofile.role, "activities": activities, "group_id": group_id, "group_name": group_name})

        context = {"form": form, "role": request.user.userprofile.role, "group_id": request.POST["group_id"]}
    else:
        group = get_object_or_404(Group, id=request.GET["group_id"])
        group_name = group.name
        if "activity_id" in request.GET:
           form = GetActivityForm(request.GET)
           context = {"form": form, "role": request.user.userprofile.role, "group_id": request.GET["group_id"], "activity_id": request.GET["activity_id"], "group_name": group_name}
        else:
           form = GetActivityForm()
           context = {"form": form, "role": request.user.userprofile.role, "group_id": request.GET["group_id"], "group_name": group_name}

    return render(request, "activity/new_activity.html", context)

@login_required
def get_chat(request):
    agent = AgentFromCsv()
    non_modifiable_output = None
    different_non_modifiable_output = False
    if "non_modifiable_output" not in request.session:
        request.session["non_modifiable_output"] = None

    if request.method == "GET":
        activity = get_object_or_404(Activity, id=request.GET["activity_id"])
    elif request.method == "POST":
        activity = get_object_or_404(Activity, id=request.POST["activity_id"])

    if request.method == "GET":
        if "stage" not in request.session:
            request.session["stage"] = 1
            request.session["num_interactions"] = 1
            request.session["suitability_counter"] = 0
            request.session["criteria_data"] = []

        if "messages" not in request.session or len(request.session["messages"]) == 0:
            system_message = {
                "text": system_prompt,
                "sender": "system",
            }

            request.session["messages"], request.session["total_messages"], non_modifiable_output = agent.apply_phase(request.session["stage"], [system_message], [system_message], activity=activity)

        additional_context = {"group_id": request.GET["group_id"], "activity_id": request.GET["activity_id"]}
    elif request.method == "POST":
        if "stage" not in request.session:
            request.session["stage"] = 1
            request.session["num_interactions"] = 1
            request.session["suitability_counter"] = 0
            request.session["criteria_data"] = []

        if agent.is_activity_finished(request.session["stage"], activity):
            messages_to_send = [{
                "text": message["text"].replace("BOT: ", "").replace("USER: ", ""),
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
            "text": "USER: "+request.POST["message"],
            "sender": "user",
        })
        request.session["total_messages"].append({
            "text": "USER: "+request.POST["message"],
            "sender": "user",
        })
        request.session.modified = True

        request.session["messages"], request.session["total_messages"], criteria, suitability, explanation = agent.apply_criteria(
            request.session["stage"],
            request.session["messages"],
            request.session["total_messages"],
            activity=activity,
            suitability_counter=request.session["suitability_counter"]
        )

        request.session["criteria_data"].append([request.session["messages"], explanation, criteria, suitability])

        if not suitability:
            request.session["suitability_counter"] += 1
            if previous_interaction is None:
                next_interaction = agent.apply_logic(request.session["stage"], criteria, activity, previous_interaction)
            else:
                next_interaction = previous_interaction
        else:
            request.session["suitability_counter"] = 0
            next_interaction = agent.apply_logic(request.session["stage"], criteria, activity, previous_interaction)

        if next_interaction == "next" or agent.are_interactions_too_many(activity, request.session["stage"], request.session["num_interactions"]):
            if agent.is_activity_finished(request.session["stage"]+1, activity):
                """request.session["messages"].append({
                    "text": "BOT: Complimenti! Hai terminato l'attività!",
                    "sender": "bot",
                })
                request.session["total_messages"].append({
                    "text": "BOT: Complimenti! Hai terminato l'attività!",
                    "sender": "bot",
                })"""
                request.session["messages"], request.session["total_messages"], previous_interaction = agent.apply_interaction(request.session["stage"], request.session["messages"], request.session["total_messages"], next_interaction, activity, end=True)

                criteria_data = request.session.get("criteria_data", [])

                if criteria_data:
                    df = pd.DataFrame(
                        criteria_data,
                        columns=["messages", "explanation", "criteria", "suitability"]
                    )

                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df.to_excel(writer, index=False)

                    excel_bytes = output.getvalue()

                    useractivity, _ = UserActivity.objects.get_or_create(
                        user_id=request.user,
                        activity_id=activity,
                    )
                    useractivity.status = useractivity.Status.DONE
                    useractivity.criteria_excel = excel_bytes
                    useractivity.save()

                    """if useractivity.criteria_excel:
                        debug_df = pd.read_excel(io.BytesIO(useractivity.criteria_excel))
                        print("DEBUG criteria_excel head:\n", debug_df.head())"""
            else:
                request.session["messages"], request.session["total_messages"], previous_interaction = agent.apply_interaction(request.session["stage"], request.session["messages"], request.session["total_messages"], next_interaction, activity, skip=False)
                if previous_interaction != -1:
                    request.session["messages"] = request.session["messages"][:-1]
                    request.session["messages"].append(request.session["total_messages"][-2])
                request.session["messages"], request.session["total_messages"], non_modifiable_output = agent.apply_phase(request.session["stage"]+1, request.session["messages"], request.session["total_messages"], activity=activity)
                if "non_modifiable_output" in request.session and non_modifiable_output.lower().strip() != request.session["non_modifiable_output"].lower().strip():
                    different_non_modifiable_output = True
                else:
                    different_non_modifiable_output = False
            request.session.modified = True
            request.session["previous_interaction"] = None
            request.session["stage"] += 1
            request.session["num_interactions"] = 1
        else:
            request.session["messages"], request.session["total_messages"], previous_interaction = agent.apply_interaction(request.session["stage"], request.session["messages"], request.session["total_messages"], next_interaction, activity)
            request.session["previous_interaction"] = previous_interaction
            if suitability:
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
        "text": message["text"].replace("BOT: ", "").replace("USER: ", ""),
        "sender": message["sender"],
    } for message in request.session["messages"] if message["sender"] != "system"]

    if non_modifiable_output is not None and non_modifiable_output.lower() != "nan" and non_modifiable_output != "":
        request.session["non_modifiable_output"] = non_modifiable_output

    return render(request, "activity/chat.html", {
        "role": request.user.userprofile.role,
        "messages": messages_to_send,
        "blocked": blocked,
        "stage": request.session["stage"],
        "non_modifiable_output": request.session["non_modifiable_output"],
        "num_stages": agent.num_stages,
        "different_non_modifiable_output": different_non_modifiable_output,
        "num_texts": agent.num_texts,
    } | additional_context)

@login_required
def get_chat_stream(request):
    agent = AgentFromCsv()
    non_modifiable_output = None
    different_non_modifiable_output = False
    session = request.session
    if "non_modifiable_output" not in request.session:
        request.session["non_modifiable_output"] = None

    if request.method == "GET":
        activity = get_object_or_404(Activity, id=request.GET["activity_id"])
    elif request.method == "POST":
        activity = get_object_or_404(Activity, id=request.POST["activity_id"])
    else:
        raise HttpResponseForbidden("Invalid request method.")

    group_name = activity.group_id.name if activity and activity.group_id else None

    if request.method == "GET":
        if "stage" not in request.session:
            request.session["stage"] = 1
            request.session["num_interactions"] = 1
            request.session["suitability_counter"] = 0
            request.session["current_num_text"] = 0
            request.session["criteria_data"] = []

        if "messages" not in request.session or len(request.session["messages"]) == 0:
            system_message = {
                "text": system_prompt,
                "sender": "system",
            }

            request.session["messages"], request.session["total_messages"], non_modifiable_output = agent.apply_phase(request.session["stage"], [system_message], [system_message], activity=activity)

        additional_context = {"group_id": request.GET["group_id"], "activity_id": request.GET["activity_id"]}

        if agent.is_activity_finished(request.session["stage"], activity):
            blocked = True
        else:
            blocked = False

        messages_to_send = [{
            "text": message["text"].replace("BOT: ", "").replace("USER: ", ""),
            "sender": message["sender"],
        } for message in request.session["messages"] if message["sender"] != "system"]

        if non_modifiable_output is not None and non_modifiable_output.lower() != "nan" and non_modifiable_output != "":
            if request.session.get("non_modifiable_output", None) != non_modifiable_output:
                request.session["current_num_text"] += 1
            request.session["non_modifiable_output"] = non_modifiable_output

        request.session["num_texts"] = agent.num_texts
        request.session.modified = True

        return render(request, "activity/chat2.html", {
            "role": request.user.userprofile.role,
            "messages": messages_to_send,
            "blocked": blocked,
            "stage": request.session["stage"],
            "non_modifiable_output": request.session["non_modifiable_output"],
            "num_stages": agent.num_stages,
            "different_non_modifiable_output": different_non_modifiable_output,
            "num_texts": session.get("num_texts"),
            "current_num_text": session.get("current_num_text"),
            "group_name": group_name,
        } | additional_context)

    elif request.method == "POST":
        if "stage" not in request.session:
            request.session["stage"] = 1
            request.session["num_interactions"] = 1
            request.session["suitability_counter"] = 0
            request.session["current_num_text"] = 0
            request.session["criteria_data"] = []

        if agent.is_activity_finished(request.session["stage"], activity):
            messages_to_send = [{
                "text": message["text"].replace("BOT: ", "").replace("USER: ", ""),
                "sender": message["sender"],
            } for message in request.session["messages"] if message["sender"] != "system"]
            additional_context = {}
            blocked = True

            useractivity = get_object_or_404(UserActivity, user_id=request.user.id, activity_id=activity.id)
            useractivity.status = useractivity.Status.DONE
            useractivity.save()

            return render(request, "activity/chat2.html",
                   {"role": request.user.userprofile.role, "messages": messages_to_send, "blocked": blocked,
                    "stage": request.session["stage"]} | additional_context)

        previous_interaction = request.session.get("previous_interaction", None)

        request.session["messages"].append({
            "text": "USER: "+request.POST["message"],
            "sender": "user",
        })
        request.session["total_messages"].append({
            "text": "USER: "+request.POST["message"],
            "sender": "user",
        })
        request.session.modified = True

        request.session["messages"], request.session["total_messages"], criteria, suitability, explanation = agent.apply_criteria(
            request.session["stage"],
            request.session["messages"],
            request.session["total_messages"],
            activity=activity,
            suitability_counter=request.session["suitability_counter"]
        )

        request.session["criteria_data"].append([request.session["messages"], explanation, criteria, suitability])

        if not suitability:
            request.session["suitability_counter"] += 1
            if previous_interaction is None:
                next_interaction = agent.apply_logic(request.session["stage"], criteria, activity, previous_interaction)
            else:
                next_interaction = previous_interaction
        else:
            request.session["suitability_counter"] = 0
            next_interaction = agent.apply_logic(request.session["stage"], criteria, activity, previous_interaction)

        if (next_interaction == "next" or agent.are_interactions_too_many(activity, request.session["stage"], request.session["num_interactions"], request.session["suitability_counter"])) and suitability:
            if agent.is_activity_finished(request.session["stage"]+1, activity):
                token_iter, finalize, previous_interaction = agent.apply_interaction(request.session["stage"], request.session["messages"], request.session["total_messages"], next_interaction, activity, criteria=criteria, streaming=True, end=True)

                criteria_data = request.session.get("criteria_data", [])

                if criteria_data:
                    df = pd.DataFrame(
                        criteria_data,
                        columns=["messages", "explanation", "criteria", "suitability"]
                    )

                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df.to_excel(writer, index=False)

                    excel_bytes = output.getvalue()

                    useractivity, _ = UserActivity.objects.get_or_create(
                        user_id=request.user,
                        activity_id=activity,
                    )
                    useractivity.status = useractivity.Status.DONE
                    useractivity.criteria_excel = excel_bytes
                    useractivity.save()
            else:
                request.session["messages"], request.session["total_messages"], previous_interaction = agent.apply_interaction(request.session["stage"], request.session["messages"], request.session["total_messages"], next_interaction, activity, criteria=criteria, skip=True)
                if previous_interaction != -1:
                    request.session["messages"] = request.session["messages"][:-1]
                    request.session["messages"].append(request.session["total_messages"][-2])
                token_iter, finalize, non_modifiable_output = agent.apply_phase(request.session["stage"]+1, request.session["messages"], request.session["total_messages"], activity=activity, streaming=True)

                if "non_modifiable_output" in request.session and non_modifiable_output.lower().strip() != request.session["non_modifiable_output"].lower().strip():
                    different_non_modifiable_output = True
                else:
                    different_non_modifiable_output = False
            request.session.modified = True
            request.session["previous_interaction"] = None
            request.session["stage"] += 1
            request.session["num_interactions"] = 1
        else:
            token_iter, finalize, previous_interaction = agent.apply_interaction(request.session["stage"], request.session["messages"], request.session["total_messages"], next_interaction, activity, criteria=criteria, streaming=True)
            request.session["previous_interaction"] = previous_interaction
            if suitability:
                request.session["num_interactions"] += 1

        request.session.modified = True

        additional_context = {"group_id": request.POST["group_id"], "activity_id": request.POST["activity_id"]}
    else:
        additional_context = {}

    if agent.is_activity_finished(request.session["stage"], activity):
        blocked = True
    else:
        blocked = False

    request.session["num_texts"] = agent.num_texts
    request.session.modified = True

    """def stream():
        # Optional: yield immediately to kick off rendering in some setups
        yield ""
        try:
            for tok in token_iter:
                yield tok
        finally:
            # Persist the full message AFTER streaming finishes (or even if client disconnects)
            request.session["messages"], request.session["total_messages"] = finalize()
            request.session.modified = True

    resp = StreamingHttpResponse(stream(), content_type="text/plain; charset=utf-8")
    resp["Cache-Control"] = "no-cache"
    resp["X-Accel-Buffering"] = "no"
    return resp"""

    def sse_event(event_name: str, data: str) -> str:
        # SSE format: event: <name>\n data: <payload>\n\n
        # data must not contain raw newlines unless you split into multiple data: lines
        data = data.replace("\r", "")
        return f"event: {event_name}\ndata: {data}\n\n"

    def stream():
        # Kick start (helps some proxies)
        yield sse_event("token", "")

        # Stream tokens
        try:
            for tok in token_iter:
                # IMPORTANT: ensure tok has no raw newlines in SSE "data:" line
                # If you need newlines, you can encode them or send multiple data: lines.
                safe_tok = tok.replace("\n", "\\n")
                yield sse_event("token", safe_tok)
        finally:
            # Finalize persisted state
            session["messages"], session["total_messages"] = finalize()
            session.modified = True

            # Build meta payload (this is what you had in the commented render)
            messages_to_send = [{
                "text": m["text"].replace("BOT: ", "").replace("USER: ", ""),
                "sender": m["sender"],
            } for m in session["messages"] if m["sender"] != "system"]

            if non_modifiable_output is not None and non_modifiable_output.lower() != "nan" and non_modifiable_output != "":
                if session.get("non_modifiable_output", None) != non_modifiable_output:
                    session["current_num_text"] += 1
                session["non_modifiable_output"] = non_modifiable_output
            session.save()

            meta = {
                "role": request.user.userprofile.role,
                "messages": messages_to_send,
                "blocked": blocked,
                "stage": session["stage"],
                "non_modifiable_output": session.get("non_modifiable_output"),
                "num_stages": agent.num_stages,
                "different_non_modifiable_output": different_non_modifiable_output,
                "group_id": request.POST.get("group_id"),
                "activity_id": request.POST.get("activity_id"),
                "num_texts": session.get("num_texts"),
                "current_num_text": session.get("current_num_text"),
                "group_name": group_name,
            } | additional_context

            yield sse_event("meta", json.dumps(meta, ensure_ascii=False))
            yield sse_event("done", "1")

    resp = StreamingHttpResponse(stream(), content_type="text/event-stream; charset=utf-8")
    resp["Cache-Control"] = "no-cache"
    resp["X-Accel-Buffering"] = "no"  # nginx
    return resp


@login_required
def download_total_messages(request):
    total_messages = request.session.get("total_messages", [])

    content = json.dumps(total_messages, indent=2, ensure_ascii=False)

    response = HttpResponse(content, content_type='application/json')
    response['Content-Disposition'] = 'attachment; filename="total_messages.json"'
    return response

@login_required
def delete_class(request):
    if request.method != "POST":
        return redirect(index)
    group_id = request.POST.get('group_id')
    group = get_object_or_404(Group, id=group_id)
    if request.user.userprofile not in group.userprofiles.all() and request.user.userprofile.role != "teacher":
         return HttpResponseForbidden("You are not allowed to delete this class.")
    group.delete()
    return redirect(index)

@login_required
def delete_activity(request):
    if request.method != "POST":
        return redirect(index)
    activity_id = request.POST.get('activity_id')
    activity = get_object_or_404(Activity, id=activity_id)
    group_id = activity.group_id.id

    if request.user.userprofile not in activity.group_id.userprofiles.all() and request.user.userprofile.role != "teacher":
         return HttpResponseForbidden("You are not allowed to delete this activity.")
    activity.delete()

    activities = Activity.objects.filter(group_id=group_id)
    return render(request, "activity/activity.html",
                  {"role": request.user.userprofile.role, "activities": activities, "group_id": group_id})
