"""
Created on 15/07/2014

@author: Andrew Robinson
"""

import logging

from galaxy.exceptions import ConfigurationError
from ..providers import AuthProvider
from galaxy.auth import _get_bool

log = logging.getLogger(__name__)


def _get_subs(d, k, params):
    if k not in d:
        raise ConfigurationError("Missing '%s' parameter in LDAP options" % k)
    return str(d[k]).format(**params)


class LDAP(AuthProvider):

    """
    Attempts to authenticate users against an LDAP server.

    If options include search-fields then it will attempt to search LDAP for
    those fields first.  After that it will bind to LDAP with the username
    (formatted as specified).
    """
    plugin_type = 'ldap'

    def authenticate(self, login, password, options):
        """
        See abstract method documentation.
        """
        log.debug("Login: %s" % login)
        log.debug("Options: %s" % options)

        failure_mode = False  # reject but continue
        if options.get('continue-on-failure', 'False') == 'False':
            failure_mode = None  # reject and do not continue

        try:
            import ldap
        except:
            log.debug(
                "Login: %s, LDAP: False (could not load ldap module)" % (login))
            return (failure_mode, '')

        # do LDAP search (if required)
        params = {'login': login, 'password': password}
        if 'search-fields' in options:
            try:
                # setup connection
                ldap.set_option(ldap.OPT_REFERRALS, 0)
                l = ldap.initialize(_get_subs(options, 'server', params))
                l.protocol_version = 3

                if 'search-user' in options:
                    l.simple_bind_s(_get_subs(options, 'search-user', params),
                                    _get_subs(options, 'search-password', params))
                else:
                    l.simple_bind_s()

                scope = ldap.SCOPE_SUBTREE

                # setup search
                attributes = [_.strip().format(**params)
                              for _ in options['search-fields'].split(',')]
                result = l.search(_get_subs(options, 'search-base', params), scope,
                                  _get_subs(options, 'search-filter', params), attributes)

                # parse results
                _, suser = l.result(result, 60)
                dn, attrs = suser[0]
                log.debug(("LDAP dn: %s" % dn))
                log.debug(("LDAP Search attributes: %s" % attrs))
                if hasattr(attrs, 'has_key'):
                    for attr in attributes:
                        if attr in attrs:
                            params[attr] = str(attrs[attr][0])
                        else:
                            params[attr] = ""
                params['dn'] = dn
            except Exception:
                log.exception('LDAP Search Exception for login: %s' % login)
                return (failure_mode, '', '')
        # end search

        # bind as user to check their credentials
        try:
            # setup connection
            ldap.set_option(ldap.OPT_REFERRALS, 0)
            l = ldap.initialize(_get_subs(options, 'server', params))
            l.protocol_version = 3
            l.simple_bind_s(_get_subs(
                options, 'bind-user', params), _get_subs(options, 'bind-password', params))
        except Exception:
            log.exception('LDAP Authentication Exception for login %s' % login)
            return (failure_mode, '', '')

        log.debug("Login: %s, LDAP: True" % (login))
        return (True,
                _get_subs(options, 'auto-register-email', params),
                _get_subs(options, 'auto-register-username', params))

    def authenticate_user(self, user, password, options):
        """
        See abstract method documentation.
        """

        if _get_bool(options, 'login-use-username', False):
            return self.authenticate(user.username, password, options)[0]
        else:
            return self.authenticate(user.email, password, options)[0]


class ActiveDirectory(LDAP):
    """ Effectively just an alias for LDAP auth, but may contain active directory specific
    logic in the future. """
    plugin_type = 'activedirectory'

__all__ = ['LDAP', 'ActiveDirectory']
