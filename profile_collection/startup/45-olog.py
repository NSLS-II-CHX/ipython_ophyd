import readline

#{{- readline.get_history_item(1)}}

TEMPLATES = {}
#TEMPLATES['long'] = """
#{{- start.plan_name }} ['{{ start.uid[:6] }}'] (scan num: {{ start.scan_id }})

TEMPLATES['long'] = """

{{- start.plan_name}} :  {{ start.motors[0]}} {{start.plan_args.start}} {{start.plan_args.stop}} {{start.plan_args.num}} ['{{ start.uid[:6] }}'] (scan num: {{ start.scan_id }})


Scan Plan
---------
{{ start.plan_type }}
{%- for k, v in start.plan_args | dictsort %}
    {{ k }}: {{ v }}
{%-  endfor %}
{% if 'signature' in start -%}
Call:
    {{ start.signature }}
{% endif %}
Metadata
--------
{% for k, v in start.items() -%}
{%- if k not in ['plan_type', 'plan_args'] -%}{{ k }} : {{ v }}
{% endif -%}


{%- endfor -%}
exposure time: TODO 
acquire  time: TODO 

"""


TEMPLATES['desc'] = """
{{- readline.get_history_item(1)}}
{{- start.plan_name }} ['{{ start.uid[:6] }}'] (scan num: {{ start.scan_id }})"""

TEMPLATES['call'] = """RE({{ start.plan_type }}(
{%- for k, v in start.plan_args.items() %}{%- if not loop.first %}   {% endif %}{{ k }}={{ v }}
{%- if not loop.last %},
{% endif %}{% endfor %}))
"""

def logbook_cb_factory(logbook_func, desc_template=None, long_template=None, attach=False):
    """Create a logbook run_start callback
    The returned function is suitable for registering as
    a 'start' callback on the the BlueSky run engine.
    Parameters
    ----------
    logbook_func : callable
        The required signature is ::
            def logbok_func(text=None, logbooks=None, tags=None, properties=None,
                            attachments=None, verify=True, ensure=False):
                '''
                Parameters
                ----------
                text : string
                    The body of the log entry.
                logbooks : string or list of strings
                    The logbooks which to add the log entry to.
                tags : string or list of strings
                    The tags to add to the log entry.
                properties : dict of property dicts
                    The properties to add to the log entry
                attachments : list of file like objects
                    The attachments to add to the log entry
                verify : bool
                    Check that properties, tags and logbooks are in the Olog
                    instance.
                ensure : bool
                    If a property, tag or logbook is not in the Olog then
                    create the property, tag or logbook before making the log
                    entry. Seting ensure to True will set verify to False.
                '''
                pass
        This matches the API on `SimpleOlogClient.log`
    """
    import jinja2
    env = jinja2.Environment()
    if long_template is None:
        long_template = TEMPLATES['long']
    if desc_template is None:
        desc_template = TEMPLATES['desc']
        #desc_template  = TEMPLATES['long']
    # It seems that the olog only has one text field, which it calls
    # `text` on the python side and 'description' on the olog side.
    # There are some CSS applications that try to shove the entire
    # thing into a single line.  We work around this by doing two
    # strings, a long one which will get put in a as an attachment
    # and a short one to go in as the 'text' which will be used as the
    # description
    long_msg = env.from_string(long_template)
    desc_msg = env.from_string(desc_template)

    def lbcb(name, doc):
        # This only applies to 'start' Documents.
        if name != 'start':
            return
        if attach:
            atch = StringIO(long_msg.render(start=doc))
             
            # monkey-patch a 'name' attribute onto StringIO
            atch.name = 'long_description.txt'
        else:
            atch=None

        desc = desc_msg.render(start=doc)
        if attach:
            logbook_func(text=desc, attachments=[atch], ensure=True)
        else:
            logbook_func(text=desc, attachments=None, ensure=True)
        
    return lbcb

 

cb = logbook_cb_factory(configured_logbook_func, desc_template=TEMPLATES['long'],attach=False)
RE.subscribe('start', cb)















