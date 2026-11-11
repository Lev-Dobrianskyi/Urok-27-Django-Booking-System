from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.contrib import messages
from django.db.models import Count, Q
from django.utils import timezone
from .models import Event, Booking
from .forms import CustomUserCreationForm, ProfileUpdateForm, EventForm


def signup(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('event_list')
    else:
        form = CustomUserCreationForm()
    return render(request, 'auth/signup.html', {'form': form})


@login_required
def profile(request):
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated!")
            return redirect('profile')
    else:
        form = ProfileUpdateForm(instance=request.user)

    now = timezone.now()
    active_bookings = request.user.bookings.filter(event__status='published', event__date__gt=now)
    canceled_bookings = request.user.bookings.filter(event__status='canceled')
    completed_bookings = request.user.bookings.filter(
        Q(event__status='completed') | Q(event__date__lte=now)
    ).exclude(event__status='canceled')

    return render(request, 'users/profile.html', {
        'form': form, 'active_bookings': active_bookings,
        'canceled_bookings': canceled_bookings, 'completed_bookings': completed_bookings
    })


def event_list(request):
    events = Event.objects.filter(status='published')

    category = request.GET.get('category')
    sort = request.GET.get('sort')
    search = request.GET.get('search')

    if category:
        events = events.filter(category__iexact=category)
    if search:
        events = events.filter(title__icontains=search)

    if sort == 'date':
        events = events.order_by('date')
    elif sort == 'popularity':
        events = events.annotate(num_bookings=Count('bookings')).order_by('-num_bookings', '-date')
    elif sort == 'price_low':
        events = events.order_by('price')
    elif sort == 'price_high':
        events = events.order_by('-price')
    else:
        events = events.order_by('-date')

    return render(request, 'events/event_list.html', {'events': events})


def event_detail(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    user_booked = False
    if request.user.is_authenticated:
        user_booked = Booking.objects.filter(user=request.user, event=event).exists()
    return render(request, 'events/event_detail.html', {'event': event, 'user_booked': user_booked})


@login_required
def book_event(request, event_id):
    event = get_object_or_404(Event, id=event_id)

    if request.method == 'POST':
        if not event.is_available_for_booking():
            messages.error(request, "Cannot book this event: It has already started, ended, or is unavailable.")
            return redirect('event_detail', event_id=event.id)

        booking = Booking(user=request.user, event=event)
        try:
            booking.full_clean()
            booking.save()
            messages.success(request, f"Successfully booked {event.title}!")
        except ValidationError as e:
            messages.error(request, e.messages[0])

    return redirect('event_detail', event_id=event.id)


@login_required
def create_event(request):
    if request.user.role not in ['admin', 'moderator'] and not request.user.is_superuser:
        messages.error(request, "Only Admins and Moderators can create events.")
        return redirect('event_list')

    if request.method == 'POST':
        form = EventForm(request.POST)
        if form.is_valid():
            event = form.save(commit=False)
            event.organizer = request.user
            event.save()
            messages.success(request, "Event created!")
            return redirect('event_detail', event_id=event.id)
    else:
        form = EventForm()
    return render(request, 'events/event_form.html', {'form': form})


@login_required
def update_event(request, event_id):
    event = get_object_or_404(Event, id=event_id)

    if request.user != event.organizer and request.user.role not in ['admin',
                                                                     'moderator'] and not request.user.is_superuser:
        messages.error(request, "You do not have permission to edit this event.")
        return redirect('event_detail', event_id=event.id)

    if request.method == 'POST':
        form = EventForm(request.POST, instance=event)
        if form.is_valid():
            form.save()
            messages.success(request, "Event updated!")
            return redirect('event_detail', event_id=event.id)
    else:
        form = EventForm(instance=event)
    return render(request, 'events/event_form.html', {'form': form})


@login_required
def delete_event(request, event_id):
    event = get_object_or_404(Event, id=event_id)

    if request.user != event.organizer and request.user.role not in ['admin',
                                                                     'moderator'] and not request.user.is_superuser:
        messages.error(request, "You do not have permission to delete this event.")
        return redirect('event_detail', event_id=event.id)

    if request.method == 'POST':
        event.delete()
        messages.success(request, "Event deleted successfully.")
        return redirect('event_list')

    return redirect('event_detail', event_id=event.id)