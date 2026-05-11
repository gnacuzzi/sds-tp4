def apply_scientific_y(*axes, scilimits=(-3, 3), fontsize=None):
    for axis in axes:
        if axis.get_yscale() != "linear":
            continue

        axis.ticklabel_format(
            axis="y",
            style="sci",
            scilimits=scilimits,
            useMathText=True,
        )

        if fontsize is not None:
            axis.yaxis.get_offset_text().set_fontsize(fontsize)
