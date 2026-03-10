from django.core.management.base import BaseCommand
from django.utils import timezone
from shop.models import VerificationCode


class Command(BaseCommand):
    help = 'Clean up expired OTP codes'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=1,
            help='Delete OTPs older than this many days (default: 1)'
        )
    
    def handle(self, *args, **options):
        days = options['days']
        cutoff_date = timezone.now() - timezone.timedelta(days=days)
        
        # Delete expired OTPs
        deleted = VerificationCode.objects.filter(
            created_at__lt=cutoff_date
        ).delete()[0]
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully deleted {deleted} expired OTP codes')
        )