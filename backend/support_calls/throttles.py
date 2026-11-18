from rest_framework.throttling import ScopedRateThrottle


class SupportCallCreateThrottle(ScopedRateThrottle):
    scope = 'support_call_create'


class SupportCallStatusThrottle(ScopedRateThrottle):
    scope = 'support_call_status'


class SupportCallTokenThrottle(ScopedRateThrottle):
    scope = 'support_call_token'


class SupportCallAdminTokenThrottle(ScopedRateThrottle):
    scope = 'support_call_admin_token'
