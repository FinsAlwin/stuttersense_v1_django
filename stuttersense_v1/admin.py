from django.contrib.admin import AdminSite
from django.contrib.auth.models import User, Group
from django.contrib.auth.admin import UserAdmin, GroupAdmin

class CustomAdminSite(AdminSite):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_app_list(self, request):
        app_list = super().get_app_list(request)
        return app_list

    class Media:
        css = {
            'all': ('admin/css/custom.css',)
        }

# Create an instance of the custom admin site
custom_admin_site = CustomAdminSite(name='custom_admin')

# Register the default models
custom_admin_site.register(User, UserAdmin)
custom_admin_site.register(Group, GroupAdmin) 