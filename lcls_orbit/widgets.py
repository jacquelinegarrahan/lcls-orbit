from typing import List, Dict
import logging
import numpy as np

from bokeh.plotting import figure
from bokeh.models import ColumnDataSource, Span, Button, ColorBar, LinearColorMapper
from bokeh.palettes import Blues9, Reds9

from lume_model.variables import TableVariable, ScalarVariable
from lume_epics.client.controller import (
    Controller
)
from lume_epics.client.monitors import PVTable, PVScalar
from bokeh.models import HoverTool


logger = logging.getLogger(__name__)


class OrbitDisplay:
    """Object holding orbit display widgets.

    """

    def __init__(
        self,
        table: TableVariable,
        controller: Controller,
        longitudinal_labels: Dict[float, str] = None,
        height: int = 400,
        width: int = 600,
        bar_width: int = None,
        color_var: ScalarVariable = None,
        color_map: list = None,
        extents: list = None,
        reference_n: int = 15
    ):

        # construct z
        self._z = []

        for row, value in table.table_data["Z"].items():
            self._z.append(value)

        self._monitor = PVTable(table, controller)
        self._controller = controller

        # validate color inputs
        if color_var is not None:
            self._color_monitor = PVScalar(color_var, controller)
            if extents is None:
                raise ValueError("Color map requires passing of extents.")
            else:
                self._extents = np.array(extents)

            if color_map is None:
                raise ValueError("Color map not provided.")
            else:
                self._color_map = color_map

        if not bar_width:
            self._bar_width = (max(self._z) - min(self._z)) / (len(self._z) + 1)
        else:
            self._bar_width = bar_width

        self._x_source = ColumnDataSource(dict(x=[], y=[], device=[], color=[]))
        self._y_source = ColumnDataSource(dict(x=[], y=[], device=[], color=[]))

        tooltips_x = [
            ("device", "@device"),
            ("value", "@y"),
            ("location", "@x{0.0}")
        ]
        
        x_hover = HoverTool(tooltips=tooltips_x)

        # set up x plot
        self.x_plot = figure(
            y_range=(-1, 1),
            x_range=(min(self._z) - self._bar_width / 2.0, max(self._z) + self._bar_width / 2.0),
            width=width,
            height=height,
            toolbar_location="right",
            title="X (mm)",
        )
        self.x_plot.vbar(x="x", bottom=0, top="y", width=self._bar_width, source=self._x_source,  color="color")
        self.x_plot.add_tools(x_hover)
        self.x_plot.xgrid.grid_line_color = None
        self.x_plot.ygrid.grid_line_color = None

        self.x_plot.xaxis.ticker.desired_num_ticks = 10
        self.x_plot.xaxis.ticker.num_minor_ticks = 10

        if longitudinal_labels:
            self.x_plot.xaxis.ticker = list(longitudinal_labels.keys())
            self.x_plot.xaxis.major_label_overrides = longitudinal_labels

        self.x_plot.ygrid.grid_line_color = None
        self.x_plot.xaxis.axis_label = "z (m)"
        self.x_plot.outline_line_color = None

        # set up y plot
        tooltips_y = [
            ("device", "@device"),
            ("value", "@y"),
            ("location", "@x{0.0}")
        ]

        y_hover = HoverTool(tooltips=tooltips_y)

        self.y_plot = figure(
            y_range=(-1, 1),
            x_range=self.x_plot.x_range,
            width=width,
            height=height,
            toolbar_location="right",
            title="Y (mm)",
        )
        self.y_plot.vbar(x="x", bottom=0, top="y", width=self._bar_width, source=self._y_source, color="color")
        self.y_plot.add_tools(y_hover)
        self.y_plot.xgrid.grid_line_color = None
        self.y_plot.ygrid.grid_line_color = None

        self.y_plot.xaxis.ticker.desired_num_ticks = 10
        self.y_plot.xaxis.ticker.num_minor_ticks = 10

        if longitudinal_labels:
         #   self.y_plot.xaxis.ticker = list(longitudinal_labels.keys())
            self.y_plot.xaxis.major_label_overrides = longitudinal_labels

        self.y_plot.ygrid.grid_line_color = None
        self.y_plot.xaxis.axis_label = "z (m)"
        self.y_plot.outline_line_color = None

        # indicator whether collecting reference
        self._collecting_reference = False
        # store reference
        self._reference_measurements = {"X": {row: [] for row in table.rows}, "Y": {row: [] for row in table.rows}}
        # how many reference steps to collect
        self._reference_n = reference_n
        self._reference_count = reference_n
        # reference button
        self.reference_button = Button(label="Collect Reference")
        self.reference_button.on_click(self._collect_reference)

        # reset button
        self.reset_reference_button = Button(label="Reset")
        self.reset_reference_button.on_click(self._reset_reference)

        self._x_ref_source = ColumnDataSource(dict(x=[], y=[]))
        self._y_ref_source = ColumnDataSource(dict(x=[], y=[]))

        # plot
        self._x_ref_line = self.x_plot.line(x="x", y="y", source=self._x_ref_source)
        self._y_ref_line = self.y_plot.line(x="x", y="y", source=self._y_ref_source)

        sxr_color_mapper = LinearColorMapper(palette=Reds9, low=extents[0], high=extents[1])
        hxr_color_mapper = LinearColorMapper(palette=Blues9, low=extents[0], high=extents[1])

        self.sxr_color_bar = ColorBar(color_mapper=sxr_color_mapper)
        self.hxr_color_bar = ColorBar(color_mapper=hxr_color_mapper)

        self.x_plot.add_layout(self.sxr_color_bar, 'right')
        self.x_plot.add_layout(self.hxr_color_bar, 'right')

        self.sxr_color_bar.visible = False

    def update_table(self, table: dict) -> None:
        """Assign new table variable.
        
        """
        self._monitor = PVTable(table, self._controller)

        self._z = []

        # caget_many
        for row, value in table.table_data["Z"].items():
            self._z.append(value)

        self._x_ref_source.data.update({"x": [], "y": []})
        self._y_ref_source.data.update({"x": [], "y": []})

        self._reference_measurements = {"X": {row: [] for row in table.rows}, "Y": {row: [] for row in table.rows}}


    def update(self) -> None:
        """
        Callback which updates the plot to reflect updated process variable values or
        new process variable.

        """
        vals = self._monitor.poll()


        if self._color_monitor is not None:
            color_val = self._color_monitor.poll()
            idx = (np.abs(self._extents - color_val)).argmin()
            color = self._color_map[idx]
            colors = [color for device in vals["X"]]

        else:
            # use default gray color
            colors = ["#695f5e" for device in vals["X"] ]

        # if collecting reference, update values
        if self._collecting_reference:
            self._reference_count -= 1

            for device in vals["X"]:
                self._reference_measurements["X"][device].append(vals["X"][device])
            
            for device in vals["Y"]:
                self._reference_measurements["Y"][device].append(vals["Y"][device])

            # check n remaining
            if self._reference_count == 0:
                self._collecting_reference=False


                x_mean = [np.mean([x for x in self._reference_measurements["X"][device] if x != None]) for device in self._reference_measurements["X"]]
                x_line_z = [self._z[i] for i, x in enumerate(x_mean) if not np.isnan(x)]
                x_mean = [x for x in x_mean if not np.isnan(x)]

                y_mean = [np.mean([y for y in self._reference_measurements["Y"][device] if y != None]) for device in self._reference_measurements["Y"]]
                y_line_z = [self._z[i] for i, y in enumerate(y_mean) if not np.isnan(y)]
                y_mean = [y for y in y_mean if not np.isnan(y)]


                for device in self._reference_measurements["X"]:
                    self._reference_measurements["X"][device] = []
                
                for device in self._reference_measurements["Y"]:
                    self._reference_measurements["Y"][device] = []

                # reset
                self._reference_count = self._reference_n

                self._x_ref_line.glyph.line_color = color
                self._y_ref_line.glyph.line_color = color


                # update plot
                self._x_ref_source.data.update({"x": x_line_z, "y": x_mean})
                self._y_ref_source.data.update({"x": y_line_z, "y": y_mean})

                
        devices = [device for device in vals['X']]
        x = np.array([vals["X"][device] for device in vals["X"]], dtype=np.float64)
        y = np.array([vals["Y"][device] for device in vals["Y"]], dtype=np.float64)

        # add hline if 0 inside
        if min(x) < 0 < max(x):
            hline = Span(
                location=0, dimension="width", line_color="black", line_width=2
            )
            self.x_plot.add_layout(hline)


        # add hline if 0 inside
        if min(y) < 0 < max(y):
            hline = Span(
                location=0, dimension="width", line_color="black", line_width=2
            )
            self.y_plot.add_layout(hline)

        self._x_source.data.update({"x": self._z, "y": x, "device": devices, "color": colors})
        self._y_source.data.update({"x": self._z, "y": y, "device": devices, "color": colors})

    def update_colormap(self, color_var: ScalarVariable, cmap: list, extents: list):
        """Update colormap and assign new PV to track for color intensity. The plots will use 
        extents passed to evaluate the PV value along a continuum and assign a color.
        
        """
        self._color_map = cmap
        self._extents = np.array(range(extents[0], extents[1], len(self._color_map)))
        self._color_monitor = PVScalar(color_var, self._controller)

    def _collect_reference(self):
        self._collecting_reference = True

    def _reset_reference(self):
        self._x_ref_source.data.update({"x": [], "y": [], "color": []})
        self._y_ref_source.data.update({"x": [], "y": [], "color": []})