from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.contrib import messages
from django.db.models import Count
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

    bookings = request.user.bookings.all().order_by('-created_at')
    active = [b for b in bookings if b.event.status == 'published' and b.event.date > timezone.now()]
    canceled = [b for b in bookings if b.event.status == 'canceled']
    completed = [b for b in bookings if b.event.status == 'completed' or b.event.date <= timezone.now()]

    return render(request, 'users/profile.html', {
        'form': form, 'active_bookings': active,
        'canceled_bookings': canceled, 'completed_bookings': completed
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
        events = events.annotate(num_bookings=Count('bookings')).order_by('-num_bookings')
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
    if request.user.role not in ['organizer', 'admin']:
        messages.error(request, "Only organizers can create events.")
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