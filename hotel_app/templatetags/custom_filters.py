from django import template

register = template.Library()

# Define the custom filter 'is_in_group' for use on html pages to check user's role
@register.filter(name='is_in_group')
def is_in_group(user, group_name):
    return user.groups.filter(name=group_name).exists()