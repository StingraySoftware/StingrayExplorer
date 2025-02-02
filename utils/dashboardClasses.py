import panel as pn
import param
from typing import List, Tuple

pn.extension("floatpanel")


class MainHeader(pn.viewable.Viewer):
    """
    MainHeader class represents the header section of the dashboard.
    It includes a heading and subheading but removes buttons.
    """

    # Parameters for the header and subheading text
    heading: str = param.String(
        default="Default Heading", doc="The heading text", allow_refs=True
    )
    subheading: str = param.String(
        default="Default Subheading", doc="The subheading text", allow_refs=True
    )

    def __init__(self, **params):
        """
        Initializes the MainHeader class with the provided parameters.
        """
        super().__init__(**params)

    def __panel__(self):
        """
        Returns the Panel layout for the header, including the heading and subheading.
        """
        # Create HTML panes for heading and subheading
        heading_pane = pn.pane.HTML(
            pn.bind(lambda heading: f"<h1>{heading}</h1>", self.param.heading)
        )

        subheading_pane = pn.pane.HTML(
            pn.bind(lambda subheading: f"<h4>{subheading}</h4>", self.param.subheading)
        )

        # Create the layout for the header
        layout_items = [heading_pane]
        if self.subheading and self.subheading != "Default Subheading":
            layout_items.append(subheading_pane)

        return pn.Column(*layout_items)


class MainArea(pn.viewable.Viewer):
    """
    MainArea class represents the main content area of the dashboard, containing multiple tabs.
    """

    # Parameter for the content of the tabs, as a dictionary with tab names as keys and content as values
    tabs_content: dict = param.Dict(
        default={},
        doc="Dictionary with tab names as keys and content as values",
        allow_refs=True,
    )

    def __init__(self, **params):
        """
        Initializes the MainArea class with the provided parameters.
        """
        super().__init__(**params)

    def __panel__(self):
        """
        Returns the Panel layout for the main area, which includes tabs with their respective content.
        """
        tabs = pn.Tabs(dynamic=True)
        for tab_name, content in self.tabs_content.items():
            tabs.append((tab_name, content))

        flexbox_layout = pn.FlexBox(
            tabs,
            sizing_mode="stretch_both",
            align_items="stretch",
            justify_content="space-between",
        )
        return flexbox_layout


class OutputBox(pn.viewable.Viewer):
    """
    OutputBox class represents a box to display output content.
    """

    # Parameter for the content to display in the output box
    output_content: str = param.String(
        default="", doc="Content to display in the output box", allow_refs=True
    )

    def __init__(self, **params):
        """
        Initializes the OutputBox class with the provided parameters.
        """
        super().__init__(**params)

    def __panel__(self):
        """
        Returns the Panel layout for the output box, including a heading and the content.
        """
        heading = pn.pane.Markdown("<h2> Output </h2>")
        output_box = pn.widgets.TextAreaInput(
            name="",
            value=self.output_content,
            disabled=True,
            min_height=220,
            sizing_mode="stretch_both",
        )
        return pn.Column(heading, output_box, sizing_mode="stretch_both")


class WarningBox(pn.viewable.Viewer):
    """
    WarningBox class represents a box to display warning content.
    """

    # Parameter for the content to display in the warning box
    warning_content: str = param.String(
        default="", doc="Content to display in the warning box", allow_refs=True
    )

    def __init__(self, **params):
        """
        Initializes the WarningBox class with the provided parameters.
        """
        super().__init__(**params)

    def __panel__(self):
        """
        Returns the Panel layout for the warning box, including a heading and the content.
        """
        heading = pn.pane.Markdown("<h2> Warning</h2>")
        warning_box = pn.widgets.TextAreaInput(
            name="",
            value=self.warning_content,
            disabled=True,
            min_height=220,
            sizing_mode="stretch_both",
        )
        return pn.Column(heading, warning_box, sizing_mode="stretch_both")


class PlotsContainer(pn.viewable.Viewer):
    """
    PlotsContainer class represents a container for displaying multiple plots.
    """

    flexbox_contents: list = param.List(default=[], doc="Contents for FlexBox containers", allow_refs=True)

    def __init__(self, *contents, **params):
        super().__init__(**params)
        self.flexbox_contents = list(contents)

    def __panel__(self):
        """
        Returns the Panel layout for the plots container.
        """
        title = pn.pane.Markdown("<h2> Plots </h2>", align="center")
        flexbox_container = pn.FlexBox(
            *self.flexbox_contents,
            flex_direction='row', 
            align_content='space-evenly', 
            align_items="center", 
            justify_content="center", 
            flex_wrap="wrap"
        )
        return pn.Column(title, flexbox_container, sizing_mode="stretch_both")

class HelpBox(pn.viewable.Viewer):
    """
    HelpBox class represents a box to display help or documentation content with tab-like functionality.
    """

    # Parameters for the title and tabbed content of the help box
    title: str = param.String(
        default="Help", doc="Title for the help box", allow_refs=True
    )
    tabs_content: dict = param.Dict(
        default={}, doc="Dictionary with tab names as keys and content as values", allow_refs=True
    )

    def __init__(self, **params):
        """
        Initializes the HelpBox class with the provided parameters.
        """
        super().__init__(**params)

    def __panel__(self):
        """
        Returns the Panel layout for the help box, including a heading and tabbed content.
        """
        heading = pn.pane.Markdown(f"<h2>{self.title}</h2>")

        # Create tabs using the provided content
        tabs = pn.Tabs(dynamic=True)
        for tab_name, content in self.tabs_content.items():
            tabs.append((tab_name, content))

        return pn.Column(heading, tabs, sizing_mode="stretch_both")



class Footer(pn.viewable.Viewer):
    """
    Footer class represents the footer section of the dashboard.
    It includes the main content, additional links, and logo.
    """

    # Parameters for the main content and additional links in the footer
    main_content: str = param.String(
        default="", doc="Main content to display in the footer", allow_refs=True
    )
    additional_links: List[str] = param.List(
        default=[], doc="List of additional links as markdown strings", allow_refs=True
    )

    def __init__(self, **params):
        """
        Initializes the Footer class with the provided parameters.
        """
        super().__init__(**params)

    def __panel__(self):
        """
        Returns the Panel layout for the footer, including logo, name, links, and contact information.
        """
        # Logo
        logo = pn.pane.PNG(
            "../assets/images/stingray_explorer.png",
            width=120,
            height=120,
            align="center",
        )
        name = pn.pane.Markdown("Stingray Explorer", align="center")

        logo_name_pane = pn.FlexBox(
            logo,
            name,
            flex_direction="column",
            justify_content="center",
            align_items="center",
        )

        # Convert Markdown links to HTML with target="_blank"
        html_links = [
            pn.pane.HTML(
                f'<a href="{link.split("(")[1][:-1]}" target="_blank">{link.split("[")[1].split("]")[0]}</a>'
            )
            for link in self.additional_links
        ]

        links_pane = pn.FlexBox(
            *html_links,
            flex_direction="column",
            justify_content="flex-start",
            align_items="center",
        )

        # Contact Us Pane
        contact_us_pane = pn.FlexBox(
            pn.pane.Markdown("Email: kartik4321mandar@gmail.com"),
            pn.pane.Markdown("Slack: @kartikmandar"),
            flex_direction="row",
            justify_content="center",
            align_items="center",
        )

        # Copyright Pane
        copyright_pane = pn.pane.Markdown(
            """
            &copy; 2025 Stingray Explorer. All rights reserved.
            """,
        )

        # Pane Layouts
        pane1 = pn.FlexBox(
            logo_name_pane,
            links_pane,
            flex_direction="row",
            justify_content="space-between",
            align_items="center",
        )

        pane2 = pn.FlexBox(
            contact_us_pane,
            flex_direction="column",
            justify_content="center",
            align_items="center",
        )

        pane3 = pn.FlexBox(
            copyright_pane,
            flex_direction="row",
            justify_content="center",
            align_items="center",
        )

        # Final Footer Layout
        footer = pn.FlexBox(
            pane1,
            pane2,
            pane3,
            flex_direction="row",
            justify_content="center",
            align_items="center",
        )

        return footer



# Custom warning handler
class WarningHandler:
    def __init__(self):
        self.warnings = []

    def warn(
        self, message, category=None, filename=None, lineno=None, file=None, line=None
    ):
        warning_message = f"Message: {message}\nCategory: {category.__name__ if category else 'N/A'}\nFile: {filename if filename else 'N/A'}\nLine: {lineno if lineno else 'N/A'}\n"
        self.warnings.append(warning_message)


class FloatingPlot(pn.viewable.Viewer):
    """
    Floating Plot Container class represents a container for displaying a single plot.
    """

    # Parameters for the title and content of Floating Panel
    title: str = param.String(default="", doc="Title for Floating Panel")
    content: pn.viewable.Viewer = param.Parameter(
        default=None, doc="Content for Floating Panel"
    )

    def __init__(self, title="", content=None, **params):
        """
        Initializes FloatingPlot class with the provided parameters.
        """
        super().__init__(**params)
        self.title = title
        self.content = content

    @property
    def object(self):
        print(f"Object property called for {self.content}")
        return self.content
    
    
    def __panel__(self):
        """
        Returns the floating panel which contains the content with the appropriate heading.
        """
        if not self.title or not self.content:
            raise ValueError("Title and content must be provided.")

        float_panel = pn.layout.FloatPanel(
            self.content,
            name=str(self.title),
            contained=False,
            position="center",
            width=700,
            height=700,
            margin=20,
            theme="success",
        )
        return float_panel

