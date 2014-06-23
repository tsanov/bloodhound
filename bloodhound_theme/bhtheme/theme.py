# -*- coding: UTF-8 -*-

#  Licensed to the Apache Software Foundation (ASF) under one
#  or more contributor license agreements.  See the NOTICE file
#  distributed with this work for additional information
#  regarding copyright ownership.  The ASF licenses this file
#  to you under the Apache License, Version 2.0 (the
#  "License"); you may not use this file except in compliance
#  with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing,
#  software distributed under the License is distributed on an
#  "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
#  KIND, either express or implied.  See the License for the
#  specific language governing permissions and limitations
#  under the License.

import sys

from collections import Counter

import fnmatch

from genshi.builder import tag
from genshi.core import TEXT, Markup
from genshi.filters.transform import Transformer
from genshi.output import DocType

from trac.config import ListOption, Option
from trac.core import Component, TracError, implements
from trac.mimeview.api import get_mimetype
from trac.resource import get_resource_url, Neighborhood, Resource
from trac.ticket.model import Ticket, Milestone
from trac.ticket.notification import TicketNotifyEmail
from trac.ticket.web_ui import TicketModule
from trac.util.compat import set
from trac.util.presentation import to_json
from trac.versioncontrol.web_ui.browser import BrowserModule
from trac.web.api import IRequestFilter, IRequestHandler, ITemplateStreamFilter
from trac.web.chrome import (add_stylesheet, add_warning, INavigationContributor,
                             ITemplateProvider, prevnext_nav, Chrome, add_script)
from trac.wiki.admin import WikiAdmin
from trac.wiki.formatter import format_to_html

from themeengine.api import ThemeBase, ThemeEngineSystem

from bhdashboard.util import dummy_request
from bhdashboard.web_ui import DashboardModule
from bhdashboard import wiki

from multiproduct.env import ProductEnvironment
from multiproduct.web_ui import PRODUCT_RE, ProductModule
from bhtheme.translation import _, add_domain

try:
    from multiproduct.ticket.web_ui import ProductTicketModule
except ImportError:
    ProductTicketModule = None

class BloodhoundTheme(ThemeBase):
    """Look and feel of Bloodhound issue tracker.
    """
    template = htdocs = css = screenshot = disable_trac_css = True
    disable_all_trac_css = True
    BLOODHOUND_KEEP_CSS = set(
        (
            'diff.css', 'code.css'
        )
    )
    BLOODHOUND_TEMPLATE_MAP = {
        # Admin
        'admin_accountsconfig.html': ('bh_admin_accountsconfig.html', '_modify_admin_breadcrumb'),
        'admin_accountsnotification.html': ('bh_admin_accountsnotification.html', '_modify_admin_breadcrumb'),
        'admin_basics.html': ('bh_admin_basics.html', '_modify_admin_breadcrumb'),
        'admin_components.html': ('bh_admin_components.html', '_modify_admin_breadcrumb'),
        'admin_enums.html': ('bh_admin_enums.html', '_modify_admin_breadcrumb'),
        'admin_logging.html': ('bh_admin_logging.html', '_modify_admin_breadcrumb'),
        'admin_milestones.html': ('bh_admin_milestones.html', '_modify_admin_breadcrumb'),
        'admin_perms.html': ('bh_admin_perms.html', '_modify_admin_breadcrumb'),
        'admin_plugins.html': ('bh_admin_plugins.html', '_modify_admin_breadcrumb'),
        'admin_products.html': ('bh_admin_products.html', '_modify_admin_breadcrumb'),
        'admin_repositories.html': ('bh_admin_repositories.html', '_modify_admin_breadcrumb'),
        'admin_users.html': ('bh_admin_users.html', '_modify_admin_breadcrumb'),
        'admin_versions.html': ('bh_admin_versions.html', '_modify_admin_breadcrumb'),

        # no template substitutions below - use the default template,
        # but call the modifier nonetheless
        'repository_links.html': ('repository_links.html', '_modify_admin_breadcrumb'),

        # Preferences
        'prefs.html': ('bh_prefs.html', None),
        'prefs_account.html': ('bh_prefs_account.html', None),
        'prefs_advanced.html': ('bh_prefs_advanced.html', None),
        'prefs_datetime.html': ('bh_prefs_datetime.html', None),
        'prefs_general.html': ('bh_prefs_general.html', None),
        'prefs_keybindings.html': ('bh_prefs_keybindings.html', None),
        'prefs_language.html': ('bh_prefs_language.html', None),
        'prefs_pygments.html': ('bh_prefs_pygments.html', None),
        'prefs_userinterface.html': ('bh_prefs_userinterface.html', None),

        # Search
        'search.html': ('bh_search.html', '_modify_search_data'),

        # Wiki
        'wiki_delete.html': ('bh_wiki_delete.html', None),
        'wiki_diff.html': ('bh_wiki_diff.html', None),
        'wiki_edit.html': ('bh_wiki_edit.html', None),
        'wiki_rename.html': ('bh_wiki_rename.html', None),
        'wiki_view.html': ('bh_wiki_view.html', '_modify_wiki_page_path'),

        # Ticket
        'diff_view.html': ('bh_diff_view.html', None),
        'manage.html': ('manage.html', '_modify_resource_breadcrumb'),
        'milestone_edit.html': ('bh_milestone_edit.html', '_modify_roadmap_page'),
        'milestone_delete.html': ('bh_milestone_delete.html', '_modify_roadmap_page'),
        'milestone_view.html': ('bh_milestone_view.html', '_modify_roadmap_page'),
        'query.html': ('bh_query.html', '_add_products_general_breadcrumb'),
        'report_delete.html': ('bh_report_delete.html', '_add_products_general_breadcrumb'),
        'report_edit.html': ('bh_report_edit.html', '_add_products_general_breadcrumb'),
        'report_list.html': ('bh_report_list.html', '_add_products_general_breadcrumb'),
        'report_view.html': ('bh_report_view.html', '_add_products_general_breadcrumb'),
        'roadmap.html': ('bh_roadmap.html', '_modify_roadmap_page'),
        'ticket.html': ('bh_ticket.html', '_modify_ticket'),
        'ticket_delete.html': ('bh_ticket_delete.html', None),
        'ticket_preview.html': ('bh_ticket_preview.html', None),

        # Attachment
        'attachment.html': ('bh_attachment.html', None),
        'preview_file.html': ('bh_preview_file.html', None),

        # Version control
        'browser.html': ('bh_browser.html', '_modify_browser'),
        'changeset.html': ('bh_changeset.html', None),
        'diff_form.html': ('bh_diff_form.html', None),
        'dir_entries.html': ('bh_dir_entries.html', None),
        'revisionlog.html': ('bh_revisionlog.html', '_modify_browser'),

        # Multi Product
        'product_view.html': ('bh_product_view.html', '_add_products_general_breadcrumb'),
        'product_list.html': ('bh_product_list.html', '_modify_product_list'),
        'product_edit.html': ('bh_product_edit.html', '_add_products_general_breadcrumb'),

        # General purpose
        'about.html': ('bh_about.html', None),
        'history_view.html': ('bh_history_view.html', None),
        'timeline.html': ('bh_timeline.html', None),

        # Account manager plugin
        'account_details.html': ('bh_account_details.html', None),
        'login.html': ('bh_login.html', None),
        'register.html': ('bh_register.html', None),
        'reset_password.html': ('bh_reset_password.html', None),
        'user_table.html': ('bh_user_table.html', None),
        'verify_email.html': ('bh_verify_email.html', None),
    }
    BOOTSTRAP_CSS_DEFAULTS = (
        # ('XPath expression', ['default', 'bootstrap', 'css', 'classes'])
        ("body//table[not(contains(@class, 'table'))]",  # TODO: Accurate ?
         ['table', 'table-condensed']),
    )

    labels_application_short = Option('labels', 'application_short',
        'Bloodhound', """A short version of application name most commonly
        displayed in text, titles and labels""", doc_domain='bhtheme')

    labels_application_full = Option('labels', 'application_full',
        'Apache Bloodhound', """This is full name with trade mark and
        everything, it is currently used in footers and about page only""",
                                     doc_domain='bhtheme')

    labels_footer_left_prefix = Option('labels', 'footer_left_prefix', '',
        """Text to display before full application name in footers""",
                                       doc_domain='bhtheme')

    labels_footer_left_postfix = Option('labels', 'footer_left_postfix', '',
        """Text to display after full application name in footers""",
                                        doc_domain='bhtheme')

    labels_footer_right = Option('labels', 'footer_right', '',
        """Text to use as the right aligned footer""", doc_domain='bhtheme')

    _wiki_pages = None
    Chrome.default_html_doctype = DocType.HTML5

    implements(IRequestFilter, INavigationContributor, ITemplateProvider,
               ITemplateStreamFilter)

    from trac.web import main
    main.default_tracker = 'http://issues.apache.org/bloodhound'

    def _get_whitelabelling(self):
        """Gets the whitelabelling config values"""
        return {
            'application_short': self.labels_application_short,
            'application_full': self.labels_application_full,
            'footer_left_prefix': self.labels_footer_left_prefix,
            'footer_left_postfix': self.labels_footer_left_postfix,
            'footer_right': self.labels_footer_right,
            'application_version': application_version
        }

    # ITemplateStreamFilter methods

    def filter_stream(self, req, method, filename, stream, data):
        """Insert default Bootstrap CSS classes if rendering
        legacy templates (i.e. determined by template name prefix)
        and renames wiki guide links.
        """
        tx = Transformer('body')

        def add_classes(classes):
            """Return a function ensuring CSS classes will be there for element.
            """
            def attr_modifier(name, event):
                attrs = event[1][1]
                class_list = attrs.get(name, '').split()
                self.log.debug('BH Theme : Element classes ' + str(class_list))

                out_classes = ' '.join(set(class_list + classes))
                self.log.debug('BH Theme : Inserting class ' + out_classes)
                return out_classes
            return attr_modifier

        # Insert default bootstrap CSS classes if necessary
        for xpath, classes in self.BOOTSTRAP_CSS_DEFAULTS:
            tx = tx.end().select(xpath) \
                .attr('class', add_classes(classes))

        # Rename wiki guide links
        tx = tx.end() \
            .select("body//a[contains(@href,'/wiki/%s')]" % wiki.GUIDE_NAME) \
            .map(lambda text: wiki.new_name(text), TEXT)

        # Rename trac error
        app_short = self.labels_application_short
        tx = tx.end() \
            .select("body//div[@class='error']/h1") \
            .map(lambda text: text.replace("Trac", app_short), TEXT)

        return stream | tx

    # IRequestFilter methods

    def pre_process_request(self, req, handler):
        """Pre process request filter"""
        def hwiki(*args, **kw):

            def new_name(name):
                new_name = wiki.new_name(name)
                if new_name != name:
                    if not self._wiki_pages:
                        wiki_admin = WikiAdmin(self.env)
                        self._wiki_pages = wiki_admin.get_wiki_list()
                    if new_name in self._wiki_pages:
                        return new_name
                return name

            a = tuple([new_name(x) for x in args])
            return req.href.__call__("wiki", *a, **kw)

        req.href.wiki = hwiki

        return handler

    def post_process_request(self, req, template, data, content_type):
        """Post process request filter.
        Removes all trac provided css if required"""

        if template is None and data is None and \
                sys.exc_info() == (None, None, None):
            return template, data, content_type

        def is_active_theme():
            is_active = False
            active_theme = ThemeEngineSystem(self.env).theme
            if active_theme is not None:
                this_theme_name = self.get_theme_names().next()
                is_active = active_theme['name'] == this_theme_name
            return is_active

        req.chrome['labels'] = self._get_whitelabelling()

        if data is not None:
            data['product_list'] = \
                ProductModule.get_product_list(self.env, req)

        links = req.chrome.get('links', {})
        # replace favicon if appropriate
        if self.env.project_icon == 'common/trac.ico':
            bh_icon = 'theme/img/bh.ico'
            new_icon = {'href': req.href.chrome(bh_icon),
                        'type': get_mimetype(bh_icon)}
            if links.get('icon'):
                links.get('icon')[0].update(new_icon)
            if links.get('shortcut icon'):
                links.get('shortcut icon')[0].update(new_icon)

        is_active_theme = is_active_theme()
        if self.disable_all_trac_css and is_active_theme:
            # Move 'admin' entry from mainnav to metanav
            for i, entry in enumerate(req.chrome['nav'].get('mainnav', [])):
                if entry['name'] == 'admin':
                    req.chrome['nav'].setdefault('metanav', []) \
                       .append(req.chrome['nav']['mainnav'].pop(i))

            if self.disable_all_trac_css:
                stylesheets = links.get('stylesheet', [])
                if stylesheets:
                    path = '/chrome/common/css/'
                    _iter = ([ss, ss.get('href', '')] for ss in stylesheets)
                    links['stylesheet'] = \
                        [ss for ss, href in _iter if not path in href or
                         href.rsplit('/', 1)[-1] in self.BLOODHOUND_KEEP_CSS]
            template, modifier = \
                self.BLOODHOUND_TEMPLATE_MAP.get(template, (template, None))
            if modifier is not None:
                modifier = getattr(self, modifier)
                modifier(req, template, data, content_type, is_active_theme)

        if is_active_theme and data is not None:
            data['responsive_layout'] = \
                self.env.config.getbool('bloodhound', 'responsive_layout',
                                        'true')
            data['bhrelations'] = \
                self.env.config.getbool('components', 'bhrelations.*', 'false')

        if req.locale is not None:
            add_script(req, 'theme/bloodhound/%s.js' % req.locale)

        return template, data, content_type

    # ITemplateProvider methods

    def get_htdocs_dirs(self):
        """Ensure dashboard htdocs will be there even if
        `bhdashboard.web_ui.DashboardModule` is disabled.
        """
        if not self.env.is_component_enabled(DashboardModule):
            return DashboardModule(self.env).get_htdocs_dirs()

    def get_templates_dirs(self):
        """Ensure dashboard templates will be there even if
        `bhdashboard.web_ui.DashboardModule` is disabled.
        """
        if not self.env.is_component_enabled(DashboardModule):
            return DashboardModule(self.env).get_templates_dirs()

    # Request modifiers

    def _modify_search_data(self, req, template, data, content_type, is_active):
        """Insert breadcumbs and context navigation items in search web UI
        """
        if is_active:
            # Insert query string in search box (see bloodhound_theme.html)
            req.search_query = data.get('query')
            # Context nav
            prevnext_nav(req, _('Previous'), _('Next'))
        # Breadcrumbs nav
        data['resourcepath_template'] = 'bh_path_search.html'

    def _modify_wiki_page_path(self, req, template, data, content_type,
                               is_active):
        """Override wiki breadcrumbs nav items
        """
        if is_active:
            data['resourcepath_template'] = 'bh_path_wikipage.html'

    def _modify_roadmap_page(self, req, template, data, content_type,
                             is_active):
        """Insert roadmap.css + products breadcrumb
        """
        add_stylesheet(req, 'dashboard/css/roadmap.css')
        self._add_products_general_breadcrumb(req, template, data,
                                              content_type, is_active)
        data['milestone_list'] = [m.name for m in Milestone.select(self.env)]
        req.chrome['ctxtnav'] = []

    def _modify_ticket(self, req, template, data, content_type, is_active):
        """Ticket modifications
        """
        self._modify_resource_breadcrumb(req, template, data, content_type,
                                         is_active)

        #add a creation event to the changelog if the ticket exists
        ticket = data['ticket']
        if ticket.exists:
            data['changes'] = [{'comment': '',
                                'author': ticket['reporter'],
                                'fields': {u'reported': {'label': u'Reported'},
                                           },
                                'permanent': 1,
                                'cnum': 0,
                                'date': ticket['time'],
                                },
                               ] + data['changes']
        #and set default order
        if not req.session.get('ticket_comments_order'):
            req.session['ticket_comments_order'] = 'newest'

    def _modify_resource_breadcrumb(self, req, template, data, content_type,
                                    is_active):
        """Provides logic for breadcrumb resource permissions
        """
        if data and ('ticket' in data.keys()) and data['ticket'].exists:
            data['resourcepath_template'] = 'bh_path_ticket.html'
            # determine path permissions
            for resname, permname in [('milestone', 'MILESTONE_VIEW'),
                                      ('product', 'PRODUCT_VIEW')]:
                res = Resource(resname, data['ticket'][resname])
                data['path_show_' + resname] = permname in req.perm(res)

            # add milestone list + current milestone to the breadcrumb
            data['milestone_list'] = [m.name
                                      for m in Milestone.select(self.env)]
            mname = data['ticket']['milestone']
            if mname:
                data['milestone'] = Milestone(self.env, mname)

    def _modify_admin_breadcrumb(self, req, template, data, content_type, is_active):
        # override 'normal' product list with the admin one

        def admin_url(prefix):
            env = ProductEnvironment.lookup_env(self.env, prefix)
            href = ProductEnvironment.resolve_href(env, self.env)
            return href.admin()

        global_settings = (None, _('(Global settings)'), admin_url(None))

        data['admin_product_list'] = [global_settings] + \
            ProductModule.get_product_list(self.env, req, admin_url)

        if isinstance(req.perm.env, ProductEnvironment):
            product = req.perm.env.product
            data['admin_current_product'] = \
                (product.prefix, product.name,
                 req.href.products(product.prefix, 'admin'))
        else:
            data['admin_current_product'] = global_settings
        data['resourcepath_template'] = 'bh_path_general.html'

    def _modify_browser(self, req, template, data, content_type, is_active):
        """Locate path to file in breadcrumbs area rather than title.
        Add browser-specific CSS.
        """
        data.update({
            'resourcepath_template': 'bh_path_links.html',
            'path_depth_limit': 2
        })
        add_stylesheet(req, 'theme/css/browser.css')

    def _add_products_general_breadcrumb(self, req, template, data,
                                         content_type, is_active):
        if isinstance(req.perm.env, ProductEnvironment):
            data['resourcepath_template'] = 'bh_path_general.html'

    def _modify_product_list(self, req, template, data, content_type,
                             is_active):
        """Transform products list into media list by adding
        configured product icon as well as further navigation items.
        """
        products = data.pop('products')
        context = data['context']
        with self.env.db_query as db:
            icons = db.execute("""
                SELECT product, value FROM bloodhound_productconfig
                WHERE product IN (%s) AND section='project' AND
                option='icon'""" % ', '.join(["%s"] * len(products)),
                tuple(p.prefix for p in products))
        icons = dict(icons)
        data['thumbsize'] = 64
        # FIXME: Gray icon for missing products
        no_thumbnail = req.href('chrome/theme/img/bh.ico')
        product_ctx = lambda item: context.child(item.resource)

        def product_media_data(icons, product):
            return dict(href=product.href(),
                        thumb=icons.get(product.prefix, no_thumbnail),
                        title=product.name,
                        description=format_to_html(self.env,
                                                   product_ctx(product),
                                                   product.description),
                        links={'extras': (([{'href': req.href.products(
                                                product.prefix, action='edit'),
                                             'title': _('Edit product %(prefix)s',
                                                        prefix=product.prefix),
                                             'icon': tag.i(class_='icon-edit'),
                                             'label': _('Edit')},]
                                           if 'PRODUCT_MODIFY' in req.perm
                                           else []) +
                                          [{'href': product.href(),
                                            'title': _('Home page'),
                                            'icon': tag.i(class_='icon-home'),
                                            'label': _('Home')},
                                           {'href': product.href.dashboard(),
                                            'title': _('Tickets dashboard'),
                                            'icon': tag.i(class_='icon-tasks'),
                                            'label': _('Tickets')},
                                           {'href': product.href.wiki(),
                                            'title': _('Wiki'),
                                            'icon': tag.i(class_='icon-book'),
                                            'label': _('Wiki')}]),
                               'main': {'href': product.href(),
                                        'title': None,
                                        'icon': tag.i(class_='icon-chevron-right'),
                                        'label': _('Browse')}})

        data['products'] = [product_media_data(icons, product)
                            for product in products]

    # INavigationContributor methods

    def get_active_navigation_item(self, req):
        return

    def get_navigation_items(self, req):
        if 'BROWSER_VIEW' in req.perm and 'VERSIONCONTROL_ADMIN' in req.perm:
            bm = self.env[BrowserModule]
            if bm and not list(bm.get_navigation_items(req)):
                yield ('mainnav', 'browser',
                       tag.a(_('Source'),
                             href=req.href.wiki('TracRepositoryAdmin')))


class QuickCreateTicketDialog(Component):
    implements(IRequestFilter, IRequestHandler)

    qct_fields = ListOption('ticket', 'quick_create_fields',
                            'product, version, type',
        doc="""Multiple selection fields displayed in create ticket menu""",
                            doc_domain='bhtheme')

    def __init__(self, *args, **kwargs):
        import pkg_resources
        locale_dir = pkg_resources.resource_filename(__name__, 'locale')
        add_domain(self.env.path, locale_dir)
        super(QuickCreateTicketDialog, self).__init__(*args, **kwargs)

    # IRequestFilter(Interface):

    def pre_process_request(self, req, handler):
        """Nothing to do.
        """
        return handler

    def post_process_request(self, req, template, data, content_type):
        """Append necessary ticket data
        """
        try:
            tm = self._get_ticket_module()
        except TracError:
            # no ticket module so no create ticket button
            return template, data, content_type

        if (template, data, content_type) != (None,) * 3:  # TODO: Check !
            if data is None:
                data = {}
            dum_req = dummy_request(self.env)
            dum_req.perm = req.perm
            ticket = Ticket(self.env)
            tm._populate(dum_req, ticket, False)
            all_fields = dict([f['name'], f]
                              for f in tm._prepare_fields(dum_req, ticket)
                              if f['type'] == 'select')

            product_field = all_fields.get('product')
            if product_field:
                # When at product scope, set the default selection to the
                # product at current scope. When at global scope the default
                # selection is determined by [ticket] default_product
                if self.env.product and \
                        self.env.product.prefix in product_field['options']:
                    product_field['value'] = self.env.product.prefix
                # Transform the options field to dictionary of product
                # attributes and filter out products for which user doesn't
                #  have TICKET_CREATE permission
                product_field['options'] = [
                    dict(value=p,
                         new_ticket_url=dum_req.href.products(p, 'newticket'),
                         description=ProductEnvironment.lookup_env(self.env, p)
                                                       .product.name
                    )
                for p in product_field['options']
                    if req.perm.has_permission('TICKET_CREATE',
                                               Neighborhood('product', p)
                                               .child(None, None))]
            else:
                msg = _("Missing ticket field '%(field)s'.", field='product')
                if ProductTicketModule is not None and \
                        self.env[ProductTicketModule] is not None:
                    # Display warning alert to users
                    add_warning(req, msg)
                else:
                    # Include message in logs since this might be a failure
                    self.log.warning(msg)
            data['qct'] = {
                'fields': [all_fields[k] for k in self.qct_fields
                           if k in all_fields],
                'hidden_fields': [all_fields[k] for k in all_fields.keys()
                                  if k not in self.qct_fields] }
        return template, data, content_type

    # IRequestHandler methods

    def match_request(self, req):
        """Handle requests sent to /qct
        """
        m = PRODUCT_RE.match(req.path_info)
        return req.path_info == '/qct' or \
            (m and m.group('pathinfo').strip('/') == 'qct')

    def process_request(self, req):
        """Forward new ticket request to `trac.ticket.web_ui.TicketModule`
        but return plain text suitable for AJAX requests.
        """
        try:
            tm = self._get_ticket_module()
            req.perm.require('TICKET_CREATE')
            summary = req.args.pop('field_summary', '')
            desc = ""
            attrs = dict([k[6:], v] for k, v in req.args.iteritems()
                         if k.startswith('field_'))
            product, tid = self.create(req, summary, desc, attrs, True)
        except Exception, exc:
            self.log.exception("BH: Quick create ticket failed %s" % (exc,))
            req.send(str(exc), 'plain/text', 500)
        else:
            tres = Neighborhood('product', product)('ticket', tid)
            href = req.href
            req.send(to_json({'product': product, 'id': tid,
                              'url': get_resource_url(self.env, tres, href)}),
                     'application/json')

    def _get_ticket_module(self):
        ptm = None
        if ProductTicketModule is not None:
            ptm = self.env[ProductTicketModule]
        tm = self.env[TicketModule]
        if not (tm is None) ^ (ptm is None):
            raise TracError('Unable to load TicketModule (disabled)?')
        if tm is None:
            tm = ptm
        return tm

    # Public API
    def create(self, req, summary, description, attributes={}, notify=False):
        """ Create a new ticket, returning the ticket ID.

        PS: Borrowed from XmlRpcPlugin.
        """
        if 'product' in attributes:
            env = self.env.parent or self.env
            if attributes['product']:
                env = ProductEnvironment(env, attributes['product'])
        else:
            env = self.env

        t = Ticket(env)
        t['summary'] = summary
        t['description'] = description
        t['reporter'] = req.authname
        for k, v in attributes.iteritems():
            t[k] = v
        t['status'] = 'new'
        t['resolution'] = ''
        t.insert()

        if notify:
            try:
                tn = TicketNotifyEmail(env)
                tn.notify(t, newticket=True)
            except Exception, e:
                self.log.exception("Failure sending notification on creation "
                                   "of ticket #%s: %s" % (t.id, e))
        return t['product'], t.id

from pkg_resources import get_distribution
application_version = get_distribution('BloodhoundTheme').version

# AutocompleteUsers and KeywordSuggestModule components basic structure is taken from
# AutocompleteUsers plugin and KeywordSuggestModule of Trac
# https://trac-hacks.org/wiki/AutocompleteUsersPlugin
# http://trac-hacks.org/wiki/KeywordSuggestPlugin

USER = 0
NAME = 1
EMAIL = 2  # indices


class AutocompleteUsers(Component):
    implements(IRequestFilter, IRequestHandler,
               ITemplateProvider, ITemplateStreamFilter)

    selectfields = ListOption('autocomplete', 'fields', default='',
                              doc='select fields to transform to autocomplete text boxes')

    # IRequestHandler methods

    def match_request(self, req):
        """Handle requests sent to /user_list and /ticket/user_list
        """
        return req.path_info.rstrip('/') == '/user_list' or req.path_info.rstrip('/') == '/ticket/user_list'

    def process_request(self, req):
        """send plain text list of users (username,email and name)
        email is shown if the EMAIL_VIEW permission is presented.
        """
        if req.args.get('users', '1') == '1':
            users = self._get_users(req)
            if req.perm.has_permission('EMAIL_VIEW'):
                subjects = ['{"label":"%s %s %s","value":"%s"}' % (user[USER] and '%s' % user[USER] or '',
                                          user[EMAIL] and '<%s>' % user[EMAIL] or '',
                                          user[NAME] and '%s' % user[NAME] or '',
                                            user[USER])
                                for value, user in users]  # value unused (placeholder needed for sorting)
            else:
                subjects = ['{"label":"%s %s","value":"%s"}' % (user[USER] and '%s' % user[USER] or '',
                                          user[NAME] and '%s' % user[NAME] or '',
                                            user[USER])
                                for value, user in users]  # value unused (placeholder needed for sorting)

        respond_str = ','.join(subjects).encode('utf-8')
        respond_str = '[' + respond_str + ']'
        req.send(respond_str, 'text/plain')

    # ITemplateProvider methods

    def get_htdocs_dirs(self):
        from pkg_resources import resource_filename

        return [('autocompleteusers', resource_filename(__name__, 'htdocs'))]

    def get_templates_dirs(self):
        return []

    # IRequestFilter methods

    def pre_process_request(self, req, handler):
        return handler

    def post_process_request(self, req, template, data, content_type):
        """add the necessary javascript and css files to ticket,permission and query page
        """
        if template in ('ticket.html', 'admin_perms.html', 'query.html'):
            add_stylesheet(req, 'autocompleteusers/css/jquery-ui-1.8.16.custom.css')
            add_script(req, 'autocompleteusers/js/jquery-ui-1.8.16.custom.min.js')
            add_script(req, 'autocompleteusers/js/format_item.js')
            if template == 'query.html':
                add_script(req, 'autocompleteusers/js/autocomplete_query.js')

        return template, data, content_type

    # ITemplateStreamFilter methods

    def filter_stream(self, req, method, filename, stream, data):
        """add the  autocomplete jQuery function to the ticket and permission pages
        """
        if filename == 'bh_ticket.html':
            fields = [field['name'] for field in data['ticket'].fields
                      if field['type'] == 'select']
            fields = set(sum([fnmatch.filter(fields, pattern)
                              for pattern in self.selectfields], []))

        js = ""

        if filename == 'bh_ticket.html':

            restrict_owner = self.env.config.getbool('ticket', 'restrict_owner')
            if req.path_info.startswith('/ticket/'):
                js = """$(document).bind('DOMSubtreeModified', function (){
                            $( "#field-cc" ).autocomplete({
                                source: "user_list"
                                multiple: true,
                                formatItem: formatItem,
                                delay: 100
                            });
                        });"""
                if not restrict_owner:
                    js = """$(document).bind('DOMSubtreeModified', function (){

                            $( "#field-cc" ).autocomplete({
                                source: "user_list",
                                multiple: true,
                                formatItem: formatItem,
                                delay: 100
                            });
                            $( "#field-reporter" ).autocomplete({
                                source: "user_list",
                                formatItem: formatItem
                            });
                        });"""
            else:

                js = """jQuery(document).ready(function($) {

                            $( "#field-cc" ).autocomplete({
                                source: "user_list"
                                multiple: true,
                                formatItem: formatItem,
                                delay: 100
                            });
                        });"""
                if not restrict_owner:
                    js = """jQuery(document).ready(function($) {

                            $( "#field-cc" ).autocomplete({
                                source: "user_list",
                                multiple: true,
                                formatItem: formatItem,
                                delay: 100
                            });
                            $( "#field-reporter" ).autocomplete({
                                source: "user_list",
                                formatItem: formatItem
                            });
                        });"""
            stream = stream | Transformer('.//head').append(tag.script(Markup(js),
                                                                   type='text/javascript'))

        elif filename == 'bh_admin_perms.html':
            users = self._get_users(req)
            subjects = ['{"label":"%s %s %s","value":"%s"}' % (user[USER] and '%s' % user[USER] or '',
                                      user[EMAIL] and '<%s>' % user[EMAIL] or '',
                                      user[NAME] and '%s' % user[NAME] or '',
                                        user[USER])
                            for value, user in users]  # value unused (placeholder needed for sorting)

            groups = self._get_groups(req)
            if groups:
                subjects_groups = ['{"label":"%s||group","value":"%s"}' % (group, group) for group in groups]
                subjects.extend(subjects_groups)

                respond_str_subjects = ','.join(subjects).encode('utf-8')
                respond_str_subjects = '[' + respond_str_subjects + ']'

                respond_str_groups = ','.join(subjects_groups).encode('utf-8')
                respond_str_groups = '[' + respond_str_groups + ']'

            js = """$(document).ready(function () {
                    var subjects =  %(subject)s
                    var groups =  %(group)s
                      $("#gp_subject").autocomplete( {
                        source: subjects,
                        formatItem: formatItem
                      });
                      $("#sg_subject").autocomplete( {
                        source: subjects,
                        formatItem: formatItem
                      });
                      $("#sg_group").autocomplete({
                        source: groups,
                        formatItem: formatItem
                      });
                    });"""
            js_ticket = js % {'subject': respond_str_subjects,
                                'group': respond_str_groups
                              }
            stream = stream | Transformer('.//head').append(tag.script(Markup(js_ticket),
                                                                   type='text/javascript'))

        return stream


    # Private methods

    def _get_groups(self, req):
        # Returns a list of groups by filtering users with session data
        # from the list of all subjects. This has the caveat of also
        # returning users without session data, but there currently seems
        # to be no other way to handle this.
        """return list of groups
        """
        query = req.args.get('term', '').lower()
        db = self.env.get_db_cnx()
        cursor = db.cursor()
        cursor.execute("""SELECT DISTINCT username FROM permission""")
        usernames = [user[0] for user in self.env.get_known_users()]
        return sorted([row[0] for row in cursor if not row[0] in usernames
        and row[0].lower().startswith(query)])

    def _get_users(self, req):
        # instead of known_users, could be
        # perm = PermissionSystem(self.env)
        # owners = perm.get_users_with_permission('TICKET_MODIFY')
        # owners.sort()
        # see: http://trac.edgewall.org/browser/trunk/trac/ticket/default_workflow.py#L232
        """return list of users
        """
        query = req.args.get('term', '').lower()

        # user names, email addresses, full names
        users = []
        for user_data in self.env.get_known_users():
            user_data = [user is not None and Chrome(self.env).format_author(req, user) or ''
                         for user in user_data]
            for index, field in enumerate((USER, EMAIL, NAME)):  # ordered by how they appear
                value = user_data[field].lower()

                if value.startswith(query):
                    users.append((2 - index, user_data))  # 2-index is the sort key
                    break
                if field == NAME:
                    lastnames = value.split()[1:]
                    if sum(name.startswith(query) for name in lastnames):
                        users.append((2 - index, user_data))  # 2-index is the sort key
                        break

        return sorted(users)

# component to suggest keywords


class KeywordSuggestModule(Component):
    implements(IRequestFilter, ITemplateProvider, ITemplateStreamFilter)

    field_opt = Option('keywordsuggest', 'field', 'keywords',
                       """Field to which the drop-down list should be attached.""")

    keywords_opt = ListOption('keywordsuggest', 'keywords', '', ',',
                              doc="A list of comma separated values available for input.")

    # IRequestFilter methods
    def pre_process_request(self, req, handler):
        return handler

    def post_process_request(self, req, template, data, content_type):
        """add the necessary javascript and css files
        """
        if req.path_info.startswith('/ticket/') or \
                req.path_info.startswith('/newticket') or \
                (req.path_info.startswith('/query')):
                add_script(req, 'keywordssuggest/js/bootstrap-tagsinput.js')
                add_stylesheet(req, 'keywordssuggest/css/bootstrap-tagsinput.css')

        return template, data, content_type

    # ITemplateStreamFilter methods
    def filter_stream(self, req, method, filename, stream, data):
        """add the jQuery tagsinput function to ticket and query pages
        """

        if not (filename == 'bh_ticket.html' or
                    (filename == 'bh_query.html')):
            return stream

        keywords = self._get_keywords_string(req)
        if not keywords:
            self.log.debug("""
                No keywords found. KeywordSuggestPlugin is disabled.""")
            keywords = []

        if filename == 'bh_ticket.html':
            if req.path_info.startswith('/ticket/'):
                js = """
                jQuery(document).ready(function($) {
                $('#field-keywords').bind('DOMSubtreeModified', function (){
                        var keywords =  %(keywords)s
                        $('%(field)s').tagsinput({
                            typeahead: {
                                source: keywords
                                }
                            });
                            });
                    });
                    """
            else:
                js = """jQuery(document).ready(function($) {
                            var keywords =  %(keywords)s


                            $('%(field)s').tagsinput({
                                typeahead: {
                                    source: keywords
                                    }
                                });
                        });"""

        if filename == 'bh_query.html':
            js = """$(document).ready(function ($) {
                          function addAutocompleteBehavior() {
                            var filters = $('#filters');
                            var contains = $.contains // jQuery 1.4+
                              || function (container, contained) {
                              while (contained !== null) {
                                if (container === contained)
                                  return true;
                                contained = contained.parentNode;
                              }
                              return false;
                            };
                            var listener = function (event) {
                              var target = event.target || event.srcElement;
                              filters.each(function () {
                                if (contains(this, target)) {
                                  var input = $(this).find('input:text').filter(function () {
                                    return target === this;
                                  });
                                  var name = input.attr('name');
                                  if (input.attr('autocomplete') !== 'off' &&
                                    /^(?:[0-9]+_)?(?:keywords)$/.test(name)) {
                                    input.tagsinput({
                                        typeahead: {
                                            source: %(keywords)s
                                            }
                                        });
                                    input.focus(); // XXX Workaround for Trac 0.12.2 and jQuery 1.4.2
                                  }
                                }
                              });
                            };
                            if ($.fn.on) {
                              // delegate method is available in jQuery 1.7+
                              filters.on('focusin', 'input:text', listener);
                            }
                            else if ($.fn.delegate) {
                              // delegate method is available in jQuery 1.4.2+
                              filters.delegate('input:text', 'focus', listener);
                            }
                            else if (window.addEventListener) {
                              // use capture=true cause focus event doesn't bubble in the default
                              filters.each(function () {
                                this.addEventListener('focus', listener, true);
                              });
                            }
                            else {
                              // focusin event bubbles, the event is avialable for IE only
                              filters.each(function () {
                                this.attachEvent('onfocusin', listener);
                              });
                            }
                          }
                          addAutocompleteBehavior();
                });"""
        # inject transient part of javascript directly into ticket.html template
        if req.path_info.startswith('/ticket/') or \
                req.path_info.startswith('/newticket'):
            js_ticket = js % {'field': '#field-' + self.field_opt,
                              'keywords': keywords
                              }
            stream = stream | Transformer('.//head').append \
                (tag.script(Markup(js_ticket),
                            type='text/javascript'))
        if req.path_info.startswith('/query'):
            js_ticket = js % {'keywords': keywords}
            stream = stream | Transformer('.//head').append \
                (tag.script(Markup(js_ticket),
                            type='text/javascript'))

        return stream

    # ITemplateProvider methods
    def get_htdocs_dirs(self):
        from pkg_resources import resource_filename

        return [('keywordssuggest', resource_filename(__name__, 'htdocs'))]

    def get_templates_dirs(self):
        from pkg_resources import resource_filename

        return [resource_filename(__name__, 'htdocs')]

    # Private methods
    def _get_keywords_string(self, req):
        """return a list of keywords relevant to the product in the frequency of usage
        """
        #currently all the keywords are taken through the db query and then sort them according to there frequency
        # get keywords from db
        db = self.env.get_db_cnx()
        cursor = db.cursor()
        product = self.env.product._data['prefix']
        sql = """SELECT t.keywords FROM ticket AS t WHERE t.keywords IS NOT null AND t.product ='%s'""" % product

        cursor.execute(sql)
        keywords = []
        for row in cursor:
            if not row[0] == '':
                row_val = str(row[0]).split(',')
                for val in row_val:
                    keywords.append(val.strip())
        # sort keywords according to frequency of occurrence
        if keywords:
            keyword_dic = Counter(keywords)
            keywords = sorted(keyword_dic, key=lambda key: -keyword_dic[key])
        else:
            keywords = ''

        return keywords
