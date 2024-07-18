import panel as pn
import param


class MainHeader(pn.viewable.Viewer):
    heading = param.String(
        default="Default Heading", doc="The heading text", allow_refs=True
    )
    subheading = param.String(
        default="Default Subheading", doc="The subheading text", allow_refs=True
    )

    button_1_name = param.String(default="Button 1", doc="Name for Button 1")
    button_2_name = param.String(default="Button 2", doc="Name for Button 2")
    button_3_name = param.String(default="Button 3", doc="Name for Button 3")
    button_4_name = param.String(default="Button 4", doc="Name for Button 4")
    button_5_name = param.String(default="Button 5", doc="Name for Button 5")
    button_6_name = param.String(default="Button 6", doc="Name for Button 6")
    button_7_name = param.String(default="Button 7", doc="Name for Button 7")
    button_8_name = param.String(default="Button 8", doc="Name for Button 8")
    button_9_name = param.String(default="Button 9", doc="Name for Button 9")
    button_10_name = param.String(default="Button 10", doc="Name for Button 10")
    button_11_name = param.String(default="Button 11", doc="Name for Button 11")
    button_12_name = param.String(default="Button 12", doc="Name for Button 12")

    button_1_action = param.Parameter(doc="Action for Button 1")
    button_2_action = param.Parameter(doc="Action for Button 2")
    button_3_action = param.Parameter(doc="Action for Button 3")
    button_4_action = param.Parameter(doc="Action for Button 4")
    button_5_action = param.Parameter(doc="Action for Button 5")
    button_6_action = param.Parameter(doc="Action for Button 6")
    button_7_action = param.Parameter(doc="Action for Button 7")
    button_8_action = param.Parameter(doc="Action for Button 8")
    button_9_action = param.Parameter(doc="Action for Button 9")
    button_10_action = param.Parameter(doc="Action for Button 10")
    button_11_action = param.Parameter(doc="Action for Button 11")
    button_12_action = param.Parameter(doc="Action for Button 12")

    def __init__(self, **params):
        super().__init__(**params)

    def __panel__(self):
        heading_pane = pn.pane.HTML(
            pn.bind(lambda heading: f"<h1>{heading}</h1>", self.param.heading)
        )
        
        subheading_pane = pn.pane.HTML(
            pn.bind(lambda subheading: f"<h2>{subheading}</h2>", self.param.subheading)
        )

        buttons = []
        if self.button_1_name and self.button_1_action:
            buttons.append(
                pn.widgets.Button(
                    name=self.button_1_name,
                    button_type="primary",
                    width=70,
                    height=30,
                    margin=(5, 5),
                    on_click=self.button_1_action,
                )
            )
        if self.button_2_name and self.button_2_action:
            buttons.append(
                pn.widgets.Button(
                    name=self.button_2_name,
                    button_type="primary",
                    width=70,
                    height=30,
                    margin=(5, 5),
                    on_click=self.button_2_action,
                )
            )
        if self.button_3_name and self.button_3_action:
            buttons.append(
                pn.widgets.Button(
                    name=self.button_3_name,
                    button_type="primary",
                    width=70,
                    height=30,
                    margin=(5, 5),
                    on_click=self.button_3_action,
                )
            )
        if self.button_4_name and self.button_4_action:
            buttons.append(
                pn.widgets.Button(
                    name=self.button_4_name,
                    button_type="primary",
                    width=70,
                    height=30,
                    margin=(5, 5),
                    on_click=self.button_4_action,
                )
            )
        if self.button_5_name and self.button_5_action:
            buttons.append(
                pn.widgets.Button(
                    name=self.button_5_name,
                    button_type="primary",
                    width=70,
                    height=30,
                    margin=(5, 5),
                    on_click=self.button_5_action,
                )
            )
        if self.button_6_name and self.button_6_action:
            buttons.append(
                pn.widgets.Button(
                    name=self.button_6_name,
                    button_type="primary",
                    width=70,
                    height=30,
                    margin=(5, 5),
                    on_click=self.button_6_action,
                )
            )
        if self.button_7_name and self.button_7_action:
            buttons.append(
                pn.widgets.Button(
                    name=self.button_7_name,
                    button_type="primary",
                    width=70,
                    height=30,
                    margin=(5, 5),
                    on_click=self.button_7_action,
                )
            )
        if self.button_8_name and self.button_8_action:
            buttons.append(
                pn.widgets.Button(
                    name=self.button_8_name,
                    button_type="primary",
                    width=70,
                    height=30,
                    margin=(5, 5),
                    on_click=self.button_8_action,
                )
            )
        if self.button_9_name and self.button_9_action:
            buttons.append(
                pn.widgets.Button(
                    name=self.button_9_name,
                    button_type="primary",
                    width=70,
                    height=30,
                    margin=(5, 5),
                    on_click=self.button_9_action,
                )
            )
        if self.button_10_name and self.button_10_action:
            buttons.append(
                pn.widgets.Button(
                    name=self.button_10_name,
                    button_type="primary",
                    width=70,
                    height=30,
                    margin=(5, 5),
                    on_click=self.button_10_action,
                )
            )
        if self.button_11_name and self.button_11_action:
            buttons.append(
                pn.widgets.Button(
                    name=self.button_11_name,
                    button_type="primary",
                    width=70,
                    height=30,
                    margin=(5, 5),
                    on_click=self.button_11_action,
                )
            )
        if self.button_12_name and self.button_12_action:
            buttons.append(
                pn.widgets.Button(
                    name=self.button_12_name,
                    button_type="primary",
                    width=70,
                    height=30,
                    margin=(5, 5),
                    on_click=self.button_12_action,
                )
            )

        layout = pn.Row(
            pn.Column(
                heading_pane,
                subheading_pane
            ),
            pn.FlexBox(
                *buttons,
                align_items="center",
                justify_content="end",
                flex_wrap="wrap",
            ),
        )

        return layout
    heading = param.String(
        default="Default Heading", doc="The heading text", allow_refs=True
    )

    button_1_name = param.String(default="Button 1", doc="Name for Button 1")
    button_2_name = param.String(default="Button 2", doc="Name for Button 2")
    button_3_name = param.String(default="Button 3", doc="Name for Button 3")
    button_4_name = param.String(default="Button 4", doc="Name for Button 4")
    button_5_name = param.String(default="Button 5", doc="Name for Button 5")
    button_6_name = param.String(default="Button 6", doc="Name for Button 6")
    button_7_name = param.String(default="Button 7", doc="Name for Button 7")
    button_8_name = param.String(default="Button 8", doc="Name for Button 8")
    button_9_name = param.String(default="Button 9", doc="Name for Button 9")
    button_10_name = param.String(default="Button 10", doc="Name for Button 10")
    button_11_name = param.String(default="Button 11", doc="Name for Button 11")
    button_12_name = param.String(default="Button 12", doc="Name for Button 12")

    button_1_action = param.Parameter(doc="Action for Button 1")
    button_2_action = param.Parameter(doc="Action for Button 2")
    button_3_action = param.Parameter(doc="Action for Button 3")
    button_4_action = param.Parameter(doc="Action for Button 4")
    button_5_action = param.Parameter(doc="Action for Button 5")
    button_6_action = param.Parameter(doc="Action for Button 6")
    button_7_action = param.Parameter(doc="Action for Button 7")
    button_8_action = param.Parameter(doc="Action for Button 8")
    button_9_action = param.Parameter(doc="Action for Button 9")
    button_10_action = param.Parameter(doc="Action for Button 10")
    button_11_action = param.Parameter(doc="Action for Button 11")
    button_12_action = param.Parameter(doc="Action for Button 12")

    def __init__(self, **params):
        super().__init__(**params)

    def __panel__(self):
        heading_pane = pn.pane.HTML(
            pn.bind(lambda heading: f"<h1>{heading}</h1>", self.param.heading)
        )

        buttons = []
        if self.button_1_name and self.button_1_action:
            buttons.append(
                pn.widgets.Button(
                    name=self.button_1_name,
                    button_type="primary",
                    width=70,
                    height=30,
                    margin=(5, 5),
                    on_click=self.button_1_action,
                )
            )
        if self.button_2_name and self.button_2_action:
            buttons.append(
                pn.widgets.Button(
                    name=self.button_2_name,
                    button_type="primary",
                    width=70,
                    height=30,
                    margin=(5, 5),
                    on_click=self.button_2_action,
                )
            )
        if self.button_3_name and self.button_3_action:
            buttons.append(
                pn.widgets.Button(
                    name=self.button_3_name,
                    button_type="primary",
                    width=70,
                    height=30,
                    margin=(5, 5),
                    on_click=self.button_3_action,
                )
            )
        if self.button_4_name and self.button_4_action:
            buttons.append(
                pn.widgets.Button(
                    name=self.button_4_name,
                    button_type="primary",
                    width=70,
                    height=30,
                    margin=(5, 5),
                    on_click=self.button_4_action,
                )
            )
        if self.button_5_name and self.button_5_action:
            buttons.append(
                pn.widgets.Button(
                    name=self.button_5_name,
                    button_type="primary",
                    width=70,
                    height=30,
                    margin=(5, 5),
                    on_click=self.button_5_action,
                )
            )
        if self.button_6_name and self.button_6_action:
            buttons.append(
                pn.widgets.Button(
                    name=self.button_6_name,
                    button_type="primary",
                    width=70,
                    height=30,
                    margin=(5, 5),
                    on_click=self.button_6_action,
                )
            )
        if self.button_7_name and self.button_7_action:
            buttons.append(
                pn.widgets.Button(
                    name=self.button_7_name,
                    button_type="primary",
                    width=70,
                    height=30,
                    margin=(5, 5),
                    on_click=self.button_7_action,
                )
            )
        if self.button_8_name and self.button_8_action:
            buttons.append(
                pn.widgets.Button(
                    name=self.button_8_name,
                    button_type="primary",
                    width=70,
                    height=30,
                    margin=(5, 5),
                    on_click=self.button_8_action,
                )
            )
        if self.button_9_name and self.button_9_action:
            buttons.append(
                pn.widgets.Button(
                    name=self.button_9_name,
                    button_type="primary",
                    width=70,
                    height=30,
                    margin=(5, 5),
                    on_click=self.button_9_action,
                )
            )
        if self.button_10_name and self.button_10_action:
            buttons.append(
                pn.widgets.Button(
                    name=self.button_10_name,
                    button_type="primary",
                    width=70,
                    height=30,
                    margin=(5, 5),
                    on_click=self.button_10_action,
                )
            )
        if self.button_11_name and self.button_11_action:
            buttons.append(
                pn.widgets.Button(
                    name=self.button_11_name,
                    button_type="primary",
                    width=70,
                    height=30,
                    margin=(5, 5),
                    on_click=self.button_11_action,
                )
            )
        if self.button_12_name and self.button_12_action:
            buttons.append(
                pn.widgets.Button(
                    name=self.button_12_name,
                    button_type="primary",
                    width=70,
                    height=30,
                    margin=(5, 5),
                    on_click=self.button_12_action,
                )
            )

        layout = pn.Row(
            heading_pane,
            pn.FlexBox(
                *buttons,
                align_items="center",
                justify_content="end",
                flex_wrap="wrap",
            ),
        )

        return layout


class MainArea(pn.viewable.Viewer):
    tabs_content = param.Dict(
        default={}, doc="Dictionary with tab names as keys and content as values"
    )

    def __init__(self, **params):
        super().__init__(**params)

    def __panel__(self):
        tabs = pn.Tabs()
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
    output_content = param.String(
        default="", doc="Content to display in the output box"
    )

    def __init__(self, **params):
        super().__init__(**params)

    def __panel__(self):
        heading = pn.pane.Markdown("## Output")
        output_box = pn.widgets.TextAreaInput(
            name="",
            value=self.output_content,
            disabled=True,
            min_height=220,
            sizing_mode="stretch_both",
        )
        return pn.Column(heading, output_box, sizing_mode="stretch_both")


class WarningBox(pn.viewable.Viewer):
    warning_content = param.String(
        default="", doc="Content to display in the warning box"
    )

    def __init__(self, **params):
        super().__init__(**params)

    def __panel__(self):
        heading = pn.pane.Markdown("## Warning")
        warning_box = pn.widgets.TextAreaInput(
            name="",
            value=self.warning_content,
            disabled=True,
            min_height=220,
            sizing_mode="stretch_both",
        )
        return pn.Column(heading, warning_box, sizing_mode="stretch_both")


class BokehPlotsContainer(pn.viewable.Viewer):
    flexbox_contents = param.List(default=[], doc="Contents for FlexBox containers")
    titles = param.List(default=[], doc="Titles for FlexBox containers")
    sizes = param.List(
        default=[], doc="Sizes for FlexBox containers as (height, width)"
    )

    def __init__(self, **params):
        super().__init__(**params)

    def __panel__(self):
        flexbox_container = pn.FlexBox(
            align_items="center", justify_content="flex-start", flex_wrap="wrap"
        )

        for idx, content in enumerate(self.flexbox_contents):
            if idx < len(self.titles):
                title = self.titles[idx]
            else:
                title = f"FlexBox {idx+1}"

            heading = pn.pane.Markdown(f"## {title}", align="center")
            flexbox = pn.Column(
                heading,
                content,
            )

            if idx < len(self.sizes):
                height, width = self.sizes[idx]
                flexbox.height = height
                flexbox.width = width
            else:
                flexbox.height = 300
                flexbox.width = 300

            flexbox_container.append(flexbox)

        return flexbox_container


class HelpBox(pn.viewable.Viewer):
    title = param.String(default="Help", doc="Title for the help box")
    help_content = param.String(default="", doc="Markdown content for the help box")

    def __init__(self, **params):
        super().__init__(**params)

    def __panel__(self):
        heading = pn.pane.Markdown(f"## {self.title}")
        help_markdown = pn.pane.Markdown(self.help_content, sizing_mode="stretch_both")
        return pn.Column(heading, help_markdown, sizing_mode="stretch_both")


class Footer(pn.viewable.Viewer):
    main_content = param.String(default="", doc="Main content to display in the footer")
    additional_links = param.List(default=[], doc="List of additional links as markdown strings")
    icons = param.List(default=[], doc="List of icon buttons")

    def __init__(self, **params):
        super().__init__(**params)

    def __panel__(self):
        logo = pn.pane.PNG(
            "../assets/images/stingray_explorer.png",
            width=100,
            height=100,
            align="center"
        )
        name = pn.pane.Markdown("Stingray Explorer", align="center")

        logo_name_pane = pn.FlexBox(
            logo,
            name,
            flex_direction="column",
            justify_content="center",
            align_items="center"
        )

        links = [pn.pane.Markdown(link) for link in self.additional_links]

        links_pane = pn.FlexBox(
            *links,
            flex_direction="column",
            justify_content="center",
            align_items="center"
        )

        icons_pane = pn.FlexBox(
            *self.icons,
            flex_direction="column",
            justify_content="center",
            align_items="center"
        )

        contact_us_pane = pn.FlexBox(
            pn.pane.Markdown("Email: contact@example.com"),
            pn.pane.Markdown("Phone: (123) 456-7890"),
            flex_direction="row",
            justify_content="center",
            align_items="center"
        )

        copyright_pane = pn.pane.Markdown(
            """
            &copy; 2024, Stingray. All rights reserved.
            """,
        )

        pane1 = pn.FlexBox(
            logo_name_pane,
            links_pane,
            icons_pane,
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

        footer = pn.FlexBox(
            pane1,
            pane2,
            pane3,
            flex_direction="row",
            justify_content="center",
            align_items="center",
    
        )

        return footer


