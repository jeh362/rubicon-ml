import warnings

import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
from dash import dcc, html
from dash.dependencies import Input, Output

from rubicon_ml.viz.base import VizBase
from rubicon_ml.viz.common.colors import (
    get_rubicon_colorscale,
    light_blue,
    plot_background_blue,
)


class DataframePlot(VizBase):
    """Plot the dataframes with name `dataframe_name` logged to the
    experiments `experiments` on a shared axis.

    Parameters
    ----------
    dataframe_name : str
        The name of the dataframe to plot. A dataframe with name
        `dataframe_name` must be logged to each experiment in `experiments`.
    experiments : list of rubicon_ml.client.experiment.Experiment, optional
        The experiments to visualize. Defaults to None. Can be set as
        attribute after instantiation.
    plotting_func : function, optional
        The `plotly.express` plotting function used to visualize the
        dataframes. Available options can be found at
        https://plotly.com/python-api-reference/plotly.express.html.
        Defaults to `plotly.express.line`.
    plotting_func_kwargs : dict, optional
        Keyword arguments to be passed to `plotting_func`. Available options
        can be found in the documentation of the individual functions at the
        URL above.
    x : str, optional
        The name of the column in the dataframes with name `dataframe_name`
        to plot across the x-axis.
    y : str, optional
        The name of the column in the dataframes with name `dataframe_name`
        to plot across the y-axis.
    """

    def __init__(
        self,
        dataframe_name,
        experiments=None,
        plotting_func=px.line,
        plotting_func_kwargs={},
        x=None,
        y=None,
    ):
        super().__init__(dash_title="plot dataframes")

        self.dataframe_name = dataframe_name
        self.experiments = experiments
        self.plotting_func = plotting_func
        self.plotting_func_kwargs = plotting_func_kwargs
        self.x = x
        self.y = y

    @property
    def layout(self):
        """Defines the dataframe plot's layout."""
        header_text = (
            f"showing dataframe '{self.dataframe_name}' "
            f"over {len(self.experiments)} experiment"
            f"{'s' if len(self.experiments) != 1 else ''}"
        )

        return html.Div(
            [
                html.Div(id="dummy-callback-trigger"),
                dbc.Row(
                    html.H5(header_text, id="header-text"),
                    className="header-row",
                ),
                dcc.Loading(dcc.Graph(id="dataframe-plot"), color=light_blue),
            ],
            id="dataframe-plot-layout-container",
        )

    def load_experiment_data(self):
        """Load the experiment data required for the dataframe plot.

        Extracts the dataframe with name `self.dataframe_name` from
        each experiment in `self.experiment` and combines the data
        stored in them into one dataframe. All dataframes with name
        `dataframe_name` must have the same schema.
        """
        self.data_df = None

        for experiment in self.experiments:
            try:
                dataframe = experiment.dataframe(name=self.dataframe_name)
            except:
                warnings.warn(
                    f"Experiment {experiment.id} does not have any dataframes logged to it."
                )
                continue

            data_df = dataframe.get_data()
            data_df["experiment_id"] = experiment.id

            if self.x is None:
                self.x = data_df.columns[0]

            if self.y is None:
                self.y = data_df.columns[1]

            if self.data_df is None:
                self.data_df = data_df
            else:
                self.data_df = pd.concat([self.data_df, data_df])

            self.data_df = self.data_df.reset_index(drop=True)

        if "color" not in self.plotting_func_kwargs:
            self.plotting_func_kwargs["color"] = "experiment_id"
        if "color_discrete_sequence" not in self.plotting_func_kwargs:
            self.plotting_func_kwargs["color_discrete_sequence"] = get_rubicon_colorscale(
                len(self.experiments),
            )
        try:
            if self.data_df.empty:
                raise Exception(f"No dataframe with name {self.dataframe_name} found!")
        except:
            if self.data_df == None:
                raise Exception(f"No dataframe with name {self.dataframe_name} found!")

    def register_callbacks(self, link_experiment_table=False):
        outputs = [
            Output("dataframe-plot", "figure"),
            Output("header-text", "children"),
        ]
        inputs = [Input("dummy-callback-trigger", "children")]
        states = []

        if link_experiment_table:
            inputs.append(
                Input("experiment-table", "derived_virtual_selected_row_ids"),
            )

        @self.app.callback(outputs, inputs, states)
        def update_dataframe_plot(*args):
            """Render the plot specified by `self.plotting_func`.

            Returns the Plotly figure generated by calling `self.plotting_func`
            on the data in the experiments' dataframes and the header text
            with the dataframes' name.
            """
            if link_experiment_table:
                selected_row_ids = args[-1]
                selected_row_ids = selected_row_ids if selected_row_ids else []
            else:
                selected_row_ids = [e.id for e in self.experiments]

            df_figure_margin = 30

            df_figure = self.plotting_func(
                self.data_df[self.data_df["experiment_id"].isin(selected_row_ids)],
                self.x,
                self.y,
                **self.plotting_func_kwargs,
            )
            df_figure.update_layout(margin_t=df_figure_margin, plot_bgcolor=plot_background_blue)

            for i in range(len(df_figure.data)):
                df_figure.data[i].name = df_figure.data[i].name[:7]

            header_text = (
                f"showing dataframe '{self.dataframe_name}' "
                f"over {len(selected_row_ids)} experiment"
                f"{'s' if len(selected_row_ids) != 1 else ''}"
            )

            return df_figure, header_text
