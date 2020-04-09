
from collections import defaultdict
from pathlib import Path
from PyQt5.uic import loadUiType

from PyQt5 import QtWidgets
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtCore import QItemSelectionModel

from ..Shared import Tab_Page_Widget
from Framework import File_System
from .VFS_Tree_Model import VFS_Tree_Model
from .VFS_List_Model import VFS_List_Model

gui_file = Path(__file__).parents[1] / 'x4c_gui_vfs_tab.ui'
generated_class, qt_base_class = loadUiType(str(gui_file))


class VFS_Window(Tab_Page_Widget, generated_class):
    '''
    Window used for displaying the virtual file system.

    Widget names:
    * widget_treeView
    * widget_listView
    * splitter
    * vsplitter
    * hsplitter
    * widget_refresh_button - TODO
    * widget_label_path
    * widget_label_details
    * widget_text_details
    * w_combobox_filetype

    Attributes:
    * window
      - The parent main window holding this tab.
    * tree_model
      - VFS_Tree_Model controlling the widget_treeView.
      - Will display directories.
    * list_model
      - QStandardItemModel controlling the widget_listView.
      - Will display files in a directory.
    * file_info_dict
      - Dict, keyed by loaded file virtual_path, holding some file
        info of interest (currently 'loaded','modified','patched','sources).
      - For use in coloring and detailed summary.
      - Gathered inside a thread for safety.
      - This will be a static dict, and references to it can be
        freely spread around to get natural updates when the dict
        contents update.
    * pattern
      - String, wildcard pattern for file paths to include.
      - Use this to limit files/folders loaded to speed up the vfs.
      - Hardcoded initially.
    * last_dialog_path
      - Path last used in the Save dialog box, to be reused.
    '''
    def __init__(self, parent, window):
        super().__init__(parent, window)
        self.file_info_dict = {}
        self.last_dialog_path = None
        # Default pattern; gets overwritten below.
        self.pattern = '.xml'
        
        # Set up initial, blank models.
        self.tree_model = VFS_Tree_Model(self, self.widget_treeView)
        self.list_model = VFS_List_Model(self, self.widget_listView)
                       
        # Trigger button for loading the table.
        #self.widget_refresh_button.clicked.connect(self.Action_Make_Table_Group)
                
        # Force the initial splitter position.
        self.hsplitter.setSizes([1000,3000])
        self.vsplitter.setSizes([3000,1000])
        
        # Set up the supported filetype patterns.
        # TODO: more as they become interesting.
        # TODO: maybe a way to select multiple.
        for pattern in [
            '*.xml',
            '*.xmf',
            '*.*',
            ]:
            self.w_combobox_filetype.addItem(pattern)
        # Set the first pattern to default.
        self.w_combobox_filetype.setCurrentIndex(0)
        
        # Catch changes to the file type combo box.
        self.w_combobox_filetype.currentIndexChanged.connect(
            self.Reset_From_File_System)
        
        return
    
    
    def Reset_From_File_System(self):
        '''
        Load the virtual paths from the File_System.
        '''
        # Disable the button while working.
        #self.widget_Table_Update.setEnabled(False)

        ## Reset the live editor table group that is be re-requested.
        ## This will fill in new items that may get created by the
        ## user script.
        #self.Queue_Thread(
        #    Live_Editor.Get_Tree_View,
        #    self.table_name, 
        #    rebuild = True,
        #    )
        
        # Update to the current combobox pattern.
        self.pattern = self.w_combobox_filetype.currentText()
        
        # Kick off the threads to update virtual paths and to
        # update the file info.
        self.Threaded_Gather_Virtual_Paths()
        self.Threaded_Gather_File_Info()

        return


    def Threaded_Gather_Virtual_Paths(self):
        '''
        Starts thread that accesses the file system and gathers all
        virtual paths, and some file summary info for loaded files.
        '''
        self.Queue_Thread(File_System.Gen_All_Virtual_Paths,
                          pattern = self.pattern,
                          callback_function = self._Threaded_Gather_Virtual_Paths_pt2)
        return

    def _Threaded_Gather_Virtual_Paths_pt2(self, virtual_paths):
        'Threaded_Gather_Virtual_Paths part 2, post-thread'    
        # Update the tree.
        self.tree_model.Set_File_Listing(virtual_paths, self.file_info_dict)
        return


    def Threaded_Gather_File_Info(self, pattern = None):
        '''
        Starts thread that gathers info on loaded files, updating
        file_info_dict.
        '''
        self.Queue_Thread(File_System.Get_Loaded_Files,
                          pattern = pattern,
                          short_run = True,
                          callback_function = self._Threaded_Gather_File_Info_pt2)
        return

    def _Threaded_Gather_File_Info_pt2(self, game_files):
        'Gather_File_Info part 2, post-thread'

        # Clear old info.
        self.file_info_dict.clear()

        # Gather generic info of interest.
        # (An alternative would be to create VFS_Item objects here, but
        # that can get clumsy to keep them up to date on soft refreshes,
        # so this will gather info to a generic dict for now that the
        # items can look into later as needed.)
        for file in game_files:
            self.file_info_dict[file.virtual_path] = {
                'loaded'  : True,
                'patched' : file.Is_Patched(),
                'modified': file.Is_Modified(),
                'sources' : file.Get_Source_Names(),
                }
            
        # Want to do soft refreshes on item displays, so they can
        # update their info and coloring.
        # The tree_model updates the list_model currently, so only
        # refresh the tree.
        self.tree_model.Soft_Refresh()
        return


    def Soft_Refresh(self):
        '''
        Does a partial refresh, redrawing the current items based
        on fresh game file information.
        TODO: replace completely with Handle_Signal
        '''
        # Do a threaded update of the file info.
        # This will update the tree automatically.
        self.Threaded_Gather_File_Info()
        return
    

    def Handle_Signal(self, *flags):
        '''
        Respond to signal events.
        '''
        if 'file_system_reset' in flags:
            self.Reset_From_File_System()
        elif 'files_loaded' in flags or 'files_modified' in flags:
            self.Threaded_Gather_File_Info()
        return

    
    def Save_Session_Settings(self, settings):
        '''
        Save aspects of the current sessions state.
        '''
        super().Save_Session_Settings(settings)
        settings.setValue('last_dialog_path', str(self.last_dialog_path))
        settings.setValue('pattern', str(self.pattern))
        return


    def Load_Session_Settings(self, settings):
        '''
        Save aspects of the prior sessions state.
        '''
        super().Load_Session_Settings(settings)
        # Note: need to capture 'None' strings and convert them.
        # Paths need to be cast to a Path if not None.
        stored_value = settings.value('last_dialog_path', None)
        if stored_value not in [None, 'None']:
            self.last_dialog_path = Path(stored_value)

        pattern = settings.value('pattern', None)
        if pattern:
            # Find the matching combobox entry and select it.
            for i in range(self.w_combobox_filetype.maxCount()):
                text = self.w_combobox_filetype.itemText(i)
                if text == pattern:
                    self.w_combobox_filetype.setCurrentIndex(i)
                    break
        
        return
