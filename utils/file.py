import os

def get_tile_suffix(col: int, row: int) -> str:
    return f"_R{(row + 1):02}_C{(col + 1):02}"

def get_tile_filepath(tile_suffix: str) -> str:
    file_extension = get_file_ext('OPEN_EXR')
    filepath = os.path.join("//PartRenders", f"Part{tile_suffix}{file_extension}")
    return filepath


def get_file_ext(file_format: str) -> str:
    """
    `file_format` can be one of the following values:
    - `BMP` BMP, Output image in bitmap format.
    - `IRIS` Iris, Output image in (old!) SGI IRIS format.
    - `PNG` PNG, Output image in PNG format.
    - `JPEG` JPEG, Output image in JPEG format.
    - `JPEG2000` JPEG 2000, Output image in JPEG 2000 format.
    - `TARGA` Targa, Output image in Targa format.
    - `TARGA_RAW` Targa Raw, Output image in uncompressed Targa format.
    - `CINEON` Cineon, Output image in Cineon format.
    - `DPX` DPX, Output image in DPX format.
    - `OPEN_EXR_MULTILAYER` OpenEXR MultiLayer, Output image in multilayer OpenEXR format.
    - `OPEN_EXR` OpenEXR, Output image in OpenEXR format.
    - `HDR` Radiance HDR, Output image in Radiance HDR format.
    - `TIFF` TIFF, Output image in TIFF format.
    """
    if file_format == 'BMP':
        return ".bmp"
    elif file_format == 'IRIS':
        return ".iris"
    elif file_format == 'PNG':
        return ".png"
    elif file_format == 'JPEG':
        return ".jpg"
    elif file_format == 'JPEG2000':
        return ".jp2"
    elif file_format in {'TARGA', 'TARGA_RAW'}:
        return ".tga"
    elif file_format == 'CINEON':
        return ".cin"
    elif file_format == 'DPX':
        return ".dpx"
    elif file_format in {'OPEN_EXR', 'OPEN_EXR_MULTILAYER'}:
        return ".exr"
    elif file_format == 'HDR':
        return ".hdr"
    elif file_format == 'TIFF':
        return ".tif"

    return "." + file_format.lower()
