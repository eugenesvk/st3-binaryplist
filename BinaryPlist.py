import sublime
from sublime import Region
import os
import sublime_plugin
from sublime_plugin import EventListener
from sublime_plugin import TextCommand
from .plistlib import plistlib
import collections

# GLOBAL STUFF
SYNTAX_FILE = 'Packages/BinaryPlist/Property_List.tmLanguage'

def is_syntax_set(view=None):
  if view is None: view = sublime.active_window().active_view()
  return 'Property_List.tmLanguage' in view.settings().get('syntax')

def is_binary_plist(view):
  return (view.substr(Region(0, 8)) == 'bplist00' \
    or    view.substr(Region(0,19)) == '6270 6c69 7374 3030')

def keys_to_strings(data):
  if   isinstance(data,            bytes    ): return      data.decode('utf-8')
  elif isinstance(data,collections.Mapping  ): return       dict(map(keys_to_strings, data.items()))
  elif isinstance(data,collections.Iterable ): return type(data)(map(keys_to_strings, data        ))
  else:                                        return      data


class BinaryPlistCommand(EventListener):
  def on_load(self, view): # Check if binary, convert to XML, mark as "was binary"
    # print('on_load')
    if is_binary_plist(view): view.run_command('binary_plist_toggle')

  def on_post_save(self, view): # Convert back to XML
    # print('on_post_save')
    if view.get_status('is_binary_plist'): view.run_command('binary_plist_toggle',{'force_to':True})

  def on_new      (self, view):
    pass # print('on_new')
  def on_clone    (self, view):
    pass # print('on_clone')
  def on_pre_close(self, view):
    pass # print('on_pre_close')
  def on_close    (self, view):
    pass # print('on_close')
  def on_pre_save(self, view):
    pass # print('on_pre_save')
  def on_modified(self, view):
    if is_binary_plist(view): view.run_command('binary_plist_toggle')
  def on_activated(self, view):
    pass # print('on_activated')

class BinaryPlistToggleCommand(TextCommand):
  def to_xml_plist(self, edit, view):
    """Reads in the view's file, converts it to XML and replaces the view's buffer with the XML text."""
    file_name = view.file_name()
    if file_name and file_name != '' and os.path.isfile(file_name) == True:
      with open(file_name, 'rb') as fp:
        pl = plistlib.load(fp)
      ctrld = {}
      cfg = sublime.load_settings("BinaryPlist.sublime-settings")
      cfgv= view.settings()
      # Save pre/pos values to document's vars so that you can't change them after load
      esc_pre= cfg.get("esc_pre"     ,None)
      esc_pos= cfg.get("esc_pos"     ,None)
      indent = cfg.get("indent"      ,None)
      sep_kv = cfg.get("key_val_sep" ,None)
      max_ll = cfg.get("max_line_len",None)
      if isinstance(esc_pre,str): cfgv.set('BinaryPlist.esc_pre'    ,esc_pre)
      else                      : esc_pre = None
      if isinstance(esc_pos,str): cfgv.set('BinaryPlist.esc_pos'    ,esc_pos)
      else                      : esc_pos = None
      if isinstance(indent ,str): cfgv.set('BinaryPlist.indent'     ,indent)
      else                      : indent  = None
      if isinstance(sep_kv ,str): cfgv.set('BinaryPlist.key_val_sep',sep_kv)
      else                      : sep_kv  = None
      if isinstance(max_ll ,int): cfgv.set('BinaryPlist.max_line_len',max_ll)
      else                      : max_ll  = None
      is_warn = cfg.get("warn_dupe",True)

      full_text = plistlib.dumps(pl,esc_pre=esc_pre,esc_pos=esc_pos, indent=indent, sep_kv=sep_kv, max_line_len=max_ll, ctrld=ctrld).decode('utf-8')
      msg_status = '⇩Binary PList'
      if ctrld.get('is_ctrl',False): msg_status += " with ❗␛Controls, see end of file…"
      if ctrld.get('is_dupe',False) and is_warn: sublime.message_dialog("This file contains the same escaped control chars used to escape actual control chars!\n\nIf you save the file, these replacement chars will be unescaped and thus lost!")
      # print("view.size()={0}".format(view.size()))
      view.replace (edit, Region(0, view.size()), full_text)
      view.end_edit(edit)
      view.set_status('is_binary_plist', msg_status)
      view.set_scratch(True)

  def to_binary_plist(self, view):
    """Converts the view's XML text back to a binary plist and writes it out to the view's file."""
    file_name = view.file_name()
    if file_name and file_name != '' and os.path.isfile(file_name) == True:
      bytes = view.substr(Region(0, view.size())).encode('utf-8')
      try:
        pl = plistlib.loads(bytes, fmt=plistlib.FMT_XML)
        with open(file_name, 'wb') as fp:
          ctrld = {}
          cfg = sublime.load_settings("BinaryPlist.sublime-settings")
          cfgv= view.settings()
          # Load pre/pos values from document's vars in case they were changed after load
          esc_pre = cfgv.get("BinaryPlist.esc_pre"     ,cfg.get("esc_pre"     ,None))
          esc_pos = cfgv.get("BinaryPlist.esc_pos"     ,cfg.get("esc_pos"     ,None))
          indent  = cfgv.get("BinaryPlist.indent"      ,cfg.get("indent"      ,None))
          sep_kv  = cfgv.get("BinaryPlist.key_val_sep" ,cfg.get("key_val_sep" ,None))
          max_ll  = cfgv.get("BinaryPlist.max_line_len",cfg.get("max_line_len",None))
          if not isinstance(esc_pre,str): esc_pre = None
          if not isinstance(esc_pos,str): esc_pos = None
          if not isinstance(indent ,str): indent  = None
          if not isinstance(sep_kv ,str): sep_kv  = None
          if not isinstance(max_ll ,int): max_ll  = None
          plistlib.dump(pl, fp, fmt=plistlib.FMT_BINARY, esc_pre=esc_pre,esc_pos=esc_pos, indent=indent, sep_kv=sep_kv, max_line_len=max_ll, ctrld=ctrld)
      except Exception as e:
        sublime.error_message(str(e))
        raise e

  def run(self, edit, force_to=False):
    if self.view.encoding() == 'UTF-8':
      if is_binary_plist(self.view) and not force_to:
        self.to_xml_plist(edit, self.view)
        if not is_syntax_set(self.view):
          self.view.set_syntax_file(SYNTAX_FILE)
      else: self.to_binary_plist(self.view)
    else:   self.view.set_encoding('UTF-8')
