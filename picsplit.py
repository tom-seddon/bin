#!env python
# from __future__ import divison
import os,PIL.Image,os.path,argparse,sys,math,collections

##########################################################################
##########################################################################

def fatal(str):
    sys.stderr.write("FATAL: %s"%str)
    if str[-1]!='\n': sys.stderr.write("\n")
    
    if emacs: raise RuntimeError
    else: sys.exit(1)

##########################################################################
##########################################################################

g_verbose=False

def v(str):
    global g_verbose
    
    if g_verbose:
        sys.stdout.write(str)
        sys.stdout.flush()

##########################################################################
##########################################################################

def is_row_transparent(im,y,min_alpha):
    for x in range(im.size[0]):
        if im.getpixel((x,y))[3]>=min_alpha: return False
    return True

def is_col_transparent(im,x,min_alpha):
    for y in range(im.size[1]):
        if im.getpixel((x,y))[3]>=min_alpha: return False
    return True

Tile=collections.namedtuple("Tile","fname box")

def main(options):
    global g_verbose ; g_verbose=options.verbose

    v("Loading: %s\n"%options.input_fname)
    image=PIL.Image.open(options.input_fname)
    v("Image size: %dx%d\n"%image.size)

    if (options.overlap_size<0 or
        options.overlap_size>=image.size[0] or
        options.overlap_size>=image.size[1]):
        fatal("bad overlap size")
    
    if options.border_min_alpha>0:
        if image.mode=="RGBA":
            while image.size[0]>0:
                if not is_col_transparent(image,0,options.border_min_alpha): break
                image=image.crop((1,0,image.size[0]-1,image.size[1]))
            while image.size[0]>0:
                if not is_col_transparent(image,image.size[0]-1,options.border_min_alpha): break
                image=image.crop((0,0,image.size[0]-1,image.size[1]))
            while image.size[1]>0:
                if not is_row_transparent(image,0,options.border_min_alpha): break
                image=image.crop((0,1,image.size[0],image.size[1]-1))
            while image.size[1]>0:
                if not is_row_transparent(image,image.size[1]-1,options.border_min_alpha): break
                image=image.crop((0,0,image.size[0],image.size[1]-1))

            if image.size[0]==0 or image.size[1]==0: fatal("Image is 0x0 after removing border")

        v("Image size without border: %dx%d\n"%image.size)

    if options.output_fname is not None:
        output_folder,output_name=os.path.split(options.output_fname)

        if output_name=="": output_name=os.path.split(options.input_fname)[1]
        if output_name=="": fatal("couldn't figure out output name to use...")

        output_fname=os.path.join(output_folder,output_name)
        output_fname_nonext,output_fname_ext=os.path.splitext(output_fname)
        
    tile_width=options.tile_width or image.size[0]
    tile_height=options.tile_height or image.size[1]

    tiles=[]
    y0=0
    while y0<image.size[1]:
        x0=0
        while x0<image.size[0]:
            x1=x0+options.tile_width
            if x1>image.size[0]: x1=image.size[0]

            y1=y0+options.tile_height
            if y1>image.size[1]: y1=image.size[1]

            box=(x0,y0,x1,y1)
            
            tile_image=image.crop(box)

            v("Tile %d: (%d,%d)-(%d,%d)\n"%(len(tiles),x0,y0,x1,y1))

            if options.output_fname is None: fname=None
            else:
                fname="%s.%d%s"%(output_fname_nonext,len(tiles),output_fname_ext)

                v("Saving: %s\n"%fname)

                if options.do_nothing: v("    (NOTE: -n specified - nothing saved)\n")
                else: tile_image.save(fname)

            tiles.append(Tile(fname,box))

            # there'd otherwise be an additional pointless sliver at
            # the edge. There must be some less stupid way of
            # detecting this, though?
            if x1==image.size[0]: break
            x0+=options.tile_width-options.overlap_size

        if y1==image.size[1]: break
        y0+=options.tile_height-options.overlap_size

    if options.xml_root_id is not None:
        # <sprite id="bg" src="04_scene06_mainImage.0.png" alignX="left" alignY="top" x="0" y="0" />
        # <sprite id="bg1" src="04_scene06_mainImage.1.png" alignX="left" alignY="top" x="1024" y="0" parent="bg" />
        # <sprite id="bg2" src="04_scene06_mainImage.2.png" alignX="left" alignY="top" x="0" y="768" parent="bg" />
        # <sprite id="bg3" src="04_scene06_mainImage.3.png" alignX="left" alignY="top" x="1024" y="768" parent="bg" />
        print
        for i,tile in enumerate(tiles):
            id=options.xml_root_id
            parent=""
            if i>0:
                id+="%d"%i
                parent='parent="%s"'%options.xml_root_id
                
            print '<sprite id="%s" src="%s" alignX="left" alignY="top" x="%d" y="%d" %s/>'%(id,
                                                                                            os.path.split(tile.fname)[1],
                                                                                            tile.box[0],
                                                                                            tile.box[1],
                                                                                            parent)
        print

    # nxtiles=(image.size[0]+tile_width-1)//tile_width
    # nytiles=(image.size[1]+tile_height-1)//tile_height
    # ntiles=nxtiles*nytiles
    
    # v("Tiles: %dx%d\n"%(nxtiles,nytiles))
    # v("Edge piece width: %d\n"%(nxtiles*options.tile_width-image.size[0]))
    # v("Edge piece height: %d\n"%(nytiles*options.tile_height-image.size[1]))

    # ndigits=int(math.ceil(math.log10(ntiles)))
    # if ndigits==0: ndigits=1

    # for i in range(ntiles):
    #     x=i%nxtiles
    #     y=i//nxtiles
            
    #     x0=x*options.tile_width
    #     x1=x0+options.tile_width

    #     y0=y*options.tile_height

    #     tile=image.crop((x0,y0,x1,y1))
        

    #     #fname="%s.%0*d%s"%(nonext,ndigits,i,ext)

    #     # Don't pad the digits. It's easier to read the result from
    #     # code that way.
    #     fname="%s.%d%s"%(nonext,i,ext)
        

##########################################################################
##########################################################################

# http://stackoverflow.com/questions/25513043/python-argparse-fails-to-parse-hex-formatting-to-int-type
def auto_int(x): return int(x,0)

def auto_int_or_none(x):
    if x=="-": return None
    else: return int(x,0)

if __name__=="__main__":
    parser=argparse.ArgumentParser(description="split image into tiles")

    parser.add_argument("-v",
                        "--verbose",
                        action="store_true",
                        help="be more verbose")

    parser.add_argument("-o",
                        dest="output_fname",
                        metavar="FILE",
                        default=None,
                        help="save tiles toe files named after %(metavar)s (tiles will be numbered automatically) (specify folder name only - e.g., -o C:\\temp\\ - to reuse input file's name)")

    parser.add_argument("-a",
                        "--border-min-alpha",
                        metavar="ALPHA",
                        default=0,
                        type=auto_int,
                        help="remove columns/rows with alpha values entirely less than %(metavar)s. (Default: %(default)s)")

    parser.add_argument("-s",
                        "--overlap-size",
                        metavar="PIXELS",
                        default=0,
                        type=auto_int,
                        help="overlap tiles by %(metavar)s pixels. (Default: %(default)s)")

    parser.add_argument("-x",
                        dest="xml_root_id",
                        metavar="NAME",
                        default=None,
                        help="print XML info with %(metavar)s as root's id (niche interest)")

    parser.add_argument("-n",
                        dest="do_nothing",
                        action="store_true",
                        help="don't actually save any files")

    parser.add_argument("tile_width",
                        metavar="WIDTH",
                        type=auto_int_or_none,
                        help="tile width, or `-' for full width of image")
    
    parser.add_argument("tile_height",
                        metavar="HEIGHT",
                        type=auto_int_or_none,
                        help="tile height, or `-' for full height of image")

    parser.add_argument("input_fname",
                        metavar="FILE",
                        help="input file")

    main(parser.parse_args(sys.argv[1:]))
    
