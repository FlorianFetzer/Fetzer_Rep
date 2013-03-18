# -*- coding: utf-8 -*-
"""
Created on Sun Mar 10 19:27:31 2013
hallo
@author: florian
"""

import numpy as np
import os
from enthought.traits.api import SingletonHasTraits, Instance, Property, Int, Float, Range,\
                                 Bool, Array, Str, Enum, Button, Tuple, List, on_trait_change,\
                                 cached_property, DelegatesTo, Trait, String, HasTraits, File
from enthought.traits.ui.api import View, Item, HGroup, VGroup, Tabbed, EnumEditor, TitleEditor, Group, TextEditor

from enthought.traits.ui.file_dialog import save_file
from enthought.traits.ui.menu import Action, Menu, MenuBar
from enthought.chaco.tools.api import PanTool, ZoomTool,LegendTool,DragZoom,TraitsTool
from enthought.chaco.example_support import COLOR_PALETTE
from enthought.enable.api import ComponentEditor, Component
from enthought.chaco.api import Plot, ScatterPlot, CMapImagePlot, ArrayPlotData,\
                                Spectral, ColorBar, LinearMapper, DataView,\
                                LinePlot, ArrayDataSource, HPlotContainer,jet,create_line_plot, Legend,\
                                add_default_grids, OverlayPlotContainer, PlotLabel,add_default_axes
#from enthought.chaco.tools.api import ZoomTool
from enthought.chaco.tools.cursor_tool import CursorTool, BaseCursorTool
from enthought.chaco.tools.image_inspector_tool import ImageInspectorTool, \
     ImageInspectorOverlay

from scipy import ndimage
from scipy import misc
from scipy.special import jn
import scipy
from enthought.chaco.api import Plot, ScatterPlot, CMapImagePlot, ArrayPlotData,\
                                Spectral, ColorBar, LinearMapper, DataView,\
                                LinePlot, ArrayDataSource, HPlotContainer
import socket

class interface(HasTraits):
    # communication attributes
    #s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    ip = String("127.0.0.1")
    port = Int(3000)
    connect=Button('connect to Server')
    send=Button('send')
    message=String()
    History= String()
    load_from_file=Button(label='load from file')
    # camera settings
    integration=Range(low=1, high=1000, value = 20, label = 'Integration')
    gain=Float(2.5, label='Gain' )
    average=Range(low=1, high=100,value=10, label= 'Average')
    gamma = Float(0.9, label = 'Gamma')
    send_settings=Button(label = 'Send Settings')
    
    image_path = File('C:/Python27/cubert/image.bmp')
    from_file=Bool(True)
    #plots
    image=Array()
    ScanData=Instance(ArrayPlotData, transient = True)
    ScanPlot=Instance(Plot, transient=True)
    ScanPlotContainer=Instance(HPlotContainer, transient=True)
    ScanImage=Instance(CMapImagePlot, transient =True)
    cursor=Instance(BaseCursorTool, transient = True)
    zoom_tool=Instance(ZoomTool, transient = True)
    TargetPlot = Instance( ScatterPlot, transient=True )
    # linePlot
    LinePlotContainer= Instance(OverlayPlotContainer, transient=True)

    cursor_line = Instance( BaseCursorTool, transient=True ) # funktioniert nicht  
    zoom_tool_line = Instance( ZoomTool,transient=True )
    plot_targets=Button(label = 'plot Targets')
    AddTargetPoint = Button(label='Add Target', desc='Append current position to List of Targets')
    RemoveTargetPoint = Button(label='Remove Target', desc='Remove Last Target from List of Targets')
    TargetList = List()
    x=Float()
    y=Float()
    x_range=Tuple(0,100)
    y_range=Tuple(0,100)
    status = String('OFFLINE')
    show_lines=Bool(False)
    # states and threads
   # state = Enum('idle', 'recieving')

    def __init__(self):
        #The delegates views don't work unless we caller the superclass __init__
        super(interface, self).__init__()
        self.on_trait_change(handler=self.set_cursor_from_position, name = 'x')
        self.on_trait_change(handler=self.set_cursor_from_position, name = 'y')
        self.cursor.on_trait_change(handler=self.set_position_from_cursor, name = 'current_position')
       # self.state2method={'receiving':self.receive}
    
    def _AddTargetPoint_changed(self):
        self.AddTarget((self.x, self.y))

    def _RemoveTargetPoint_changed(self):
        self.RemoveTarget()    
    
    def AddTarget(self, position, index=None):
        if index is None:
            self.TargetList.append( position )
        else:
            self.TargetList.insert(index, position )
        self._TargetList_changed()

    def RemoveTarget(self, index=None):
        if index is None:
            self.TargetList.pop()
        else:
            self.TargetList.pop(index)
        self._TargetList_changed()    
        
    def _TargetList_changed(self):
        if len(self.TargetList) == 0:
            self.ScanData.set_data('x', np.array(()))
            self.ScanData.set_data('y', np.array(()))
        else:
            positions = np.array(self.TargetList)
            self.ScanData.set_data('x', positions[:,0])
            self.ScanData.set_data('y', positions[:,1])
        print self.TargetList
        
        
    def _image_default(self):
        return np.zeros((self.x_range[1], self.y_range[1]))
    def _ScanData_default(self):
        return ArrayPlotData(image=self.image, x=np.array(()), y=np.array(()))
    def _ScanPlot_default(self):
        return Plot(self.ScanData, resizable='hv', aspect_ratio=1.0, title='image')
    def _TargetPlot_default(self):
        return self.ScanPlot.plot( ('x', 'y'), type='scatter', marker='cross', marker_size=6, line_width=1.0, color='black')[0]
    def _ScanImage_default(self):
        return self.ScanPlot.img_plot('image',xbounds=(self.x_range[0],self.x_range[-1]), ybounds=(self.y_range[0], self.y_range[-1]))[0]      
    def _cursor_default(self):
        cursor = CursorTool(self.ScanImage,
                            drag_button='left',
                            color='blue',
                            line_width=1.0 )
        cursor._set_current_position('x', (self.x, self.y))
        return cursor
    def _zoom_tool_default(self):
        return ZoomTool(self.ScanImage, enable_wheel=False)
    def _ScanPlotContainer_default(self):
        ScanImage = self.ScanImage
        ScanImage.x_mapper.domain_limits = (self.x_range[0],self.x_range[1])
        ScanImage.y_mapper.domain_limits = (self.y_range[0],self.y_range[1])
        ScanImage.overlays.append(self.zoom_tool)
        ScanImage.overlays.append(self.cursor)
        #colormap = ScanImage.color_mapper
#        colorbar = ColorBar(index_mapper=LinearMapper(range=colormap.range),
#                            color_mapper=colormap,
#                            plot=self.ScanPlot,
#                            orientation='v',
#                            resizable='v',
#                            width=20,
#                            height=400,
#                            padding=50)

        container = HPlotContainer()
        container.add(self.ScanPlot)
        #container.add(colorbar)

        return container

        
    def _image_changed(self):
        self.ScanData.set_data('image', self.image)
        self.ScanPlot.request_redraw()

    def set_cursor_from_position(self):
        self.cursor.on_trait_change(handler=self.set_position_from_cursor, name='current_position', remove=True) 
        self.cursor.current_position = (self.x, self.y)
        self.cursor.on_trait_change(handler=self.set_position_from_cursor, name='current_position')

    def set_position_from_cursor(self):
        self.on_trait_change(handler=self.set_cursor_from_position, name='x', remove=True)
        self.on_trait_change(handler=self.set_cursor_from_position, name='y', remove=True)
        self.x, self.y = self.cursor.current_position
        self.on_trait_change(handler=self.set_cursor_from_position, name='x')
        self.on_trait_change(handler=self.set_cursor_from_position, name='y')


    def _load_from_file_fired(self):   
        self.image=np.random.rand(self.x_range[1], self.y_range[1])
        
    def _LinePlotContainer_default(self):
        container = OverlayPlotContainer(padding = 50, fill_padding = True,
                                     bgcolor = "lightgray", use_backbuffer=True)
        
        print 'hallo'
        return container
        
    def _plot_targets_fired(self):
        print 'bla'
        numpoints = 100
        low = -5
        high = 15.0
        x = np.arange(low, high+0.001, (high-low)/numpoints)
        # Plot some bessel functions
        value_mapper = None
        index_mapper = None
        plots = {}
        for i in range(10):
            y = jn(i, x)
            plot = create_line_plot((x,y), color=tuple(COLOR_PALETTE[i]), width=2.0)
            #plot.index.sort_order = "ascending"

            plot.bgcolor = "white"
            plot.border_visible = True
            if i != 0:
                plot.value_mapper = value_mapper
                value_mapper.range.add(plot.value)
                plot.index_mapper = index_mapper
                index_mapper.range.add(plot.index)
            else:
                value_mapper = plot.value_mapper
                index_mapper = plot.index_mapper
                add_default_grids(plot)
                add_default_axes(plot)
                plot.index_range.tight_bounds = False
                plot.index_range.refresh()
                plot.value_range.tight_bounds = False
                plot.value_range.refresh()
                plot.tools.append(PanTool(plot))
               
                # The ZoomTool tool is stateful and allows drawing a zoom
                # box to select a zoom region.
                zoom = ZoomTool(plot, tool_mode="box", always_on=False)
                plot.overlays.append(zoom)
                # The DragZoom tool just zooms in and out as the user drags
                # the mouse vertically.
                dragzoom = DragZoom(plot, drag_button="right")
                plot.tools.append(dragzoom)
                # Add a legend in the upper right corner, and make it relocatable
                legend = Legend(component=plot, padding=10, align="ur")
                legend.tools.append(LegendTool(legend, drag_button="right"))
                plot.overlays.append(legend)
            self.LinePlotContainer.add(plot)
            plots["Bessel j_%d"%i] = plot
        # Set the list of plots on the legend
        legend.plots = plots
        # Add the title at the top
        self.LinePlotContainer.overlays.append(PlotLabel("Bessel functions",
                                  component=self.LinePlotContainer,
                                  font = "swiss 16",
                                  overlay_position="top"))
        # Add the traits inspector tool to the container
        self.LinePlotContainer.tools.append(TraitsTool(self.LinePlotContainer))
        self.show_lines=True
        print 'hallo'
            
    def _connect_fired(self):
        try:
            self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.s.connect((self.ip, self.port))
            self.status = 'CONNECTED'
            del self.s
            return 0
        except:
            print 'error'
            self.status='CONNECTION ERROR'
            return 1

            
    def _send_settings_fired(self):
        """  sends commands to adjust the settings to the server """
        self._send('<Cmd>SetInt="' +str(self.integration)+ '"</Cmd>')
        self._receive()
        self._send('<Cmd>SetGan="' +str(self.gain)+ '"</Cmd>')
        self._receive()
        self._send('<Cmd>SetAvg="'+str(self.average)+ '"</Cmd>')
        self._receive()
        self._send('<Cmd>SetGamma="' +str(self.gamma)+ '"</Cmd>')
        self._receive()
        return 0
            
    def _send_fired(self):
        try:
            # open socket
            self._send(self.message)       
            self._receive()
            self.message = ''            
            return 0
        except:
            self.History = self.History + "ERROR SENDING: " + self.message + "\n"
            return 1
            
    def _send(self, msg):
        print 'start send'
        self.message = msg
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.connect((self.ip, self.port))
        totalsent = 0
        while totalsent < len(msg):
            sent = self.s.send(msg[totalsent:])
            if sent == 0:
                raise RuntimeError("socket connection broken")
            totalsent = totalsent + sent
        self.History = self.History  + self.message + "\n"
        print 'end send'
        
    def _receive(self):
        msg = ''
        print 'start rec.'
        while len(msg) < len(self.message):
            chunk = self.s.recv(len('received:' + self.message)-len(msg))
            if chunk == '':
                raise RuntimeError("socket connection broken")
            msg = msg + chunk
        del self.s
        print 'end_receive'
        print msg
        self.History = self.History  + msg + "\n"
        self.message=''
        return msg
        
    MainView= View(Item('status', style='readonly'), 
                   Tabbed(HGroup(HGroup(VGroup(Item('ScanPlotContainer', editor=ComponentEditor(), show_label=False, resizable=True),HGroup(Item('AddTargetPoint'), Item('RemoveTargetPoint'), Item('plot_targets'), Item('show_lines'), Item('x'), Item('y'))),Group(Item('LinePlotContainer', editor=ComponentEditor(), show_label=False, resizable=True ),visible_when='show_lines')) ,label = 'Data'), 
                          Group(HGroup(VGroup(Item('status', style='readonly'), Item('ip'), Item('port'), Item('connect')), VGroup(Item('integration'), Item('gain'), Item('average'), Item('gamma'), Item('send_settings'))),VGroup(Item('History', springy=True, style='custom'), Item('message'),Item('send'), Item('from_file'),
                                 Item('image_path', style='custom', visible_when='from_file'), Item('load_from_file')), label = 'Connection')), resizable=True, title = 'CUBERT Interface')



if __name__=='__main__':
    i=interface()
    i.edit_traits()
