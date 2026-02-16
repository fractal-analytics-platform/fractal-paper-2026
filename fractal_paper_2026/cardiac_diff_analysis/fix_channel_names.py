import ngio

plate_url = ""
acquisition = 5  # Which acquisition to fix, None if acquisitions are unset
channel_switches = [
    {"from": "NKX2-5", "wavelength_id": "A02_C03", "to": "bCatenin"},
    {"from": "bCatenin", "wavelength_id": "A01_C02", "to": "NKX2-5"},
]

plate = ngio.open_ome_zarr_plate(plate_url, mode="r+")
image_list = plate.images_paths(acquisition=acquisition)
for image_path in image_list:
    row, col, path = image_path.split("/")
    image = plate.get_image(row=row, column=col, image_path=path)
    channel_meta = image.image_meta.channels_meta
    ch_meta = image.image_meta.channels_meta
    channels = ch_meta.channels

    new_labels = []
    wavelength_ids = []

    colors = []
    active = []
    starts = []
    ends = []

    for ch in channels:
        # start from the original label
        label = ch.label

        for channel_switch in channel_switches:
            if (
                label == channel_switch["from"]
                and ch.wavelength_id == channel_switch["wavelength_id"]
            ):
                label = channel_switch["to"]
                print(
                    f"Swapped {channel_switch['from']} to {channel_switch['to']} in image: {image_path} "
                    f"for channel {ch.wavelength_id}"
                )

        new_labels.append(label)
        wavelength_ids.append(ch.wavelength_id)
        colors.append(ch.channel_visualisation.color)
        active.append(ch.channel_visualisation.active)
        starts.append(ch.channel_visualisation.start)
        ends.append(ch.channel_visualisation.end)

    # Now write a *new* ChannelsMeta via the ngio API
    # Access private API to set start & end values
    images_container = image._images_container
    images_container.set_channel_meta(
        labels=new_labels,
        wavelength_id=wavelength_ids,
        colors=colors,
        active=active,
        start=starts,
        end=ends,
    )
