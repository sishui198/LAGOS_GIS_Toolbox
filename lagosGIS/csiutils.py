#-------------------------------------------------------------------------------
# Name:        csiutils
# Purpose: To provide a number of small functions called repeatedly throughout the CSI Limnology toolbox that users do not need to access, only developers
#
# Author:      CSI
#
# Created:     19/12/2013

#-------------------------------------------------------------------------------
import csv, os, tempfile
import arcpy
import numpy

def main():
    pass

if __name__ == '__main__':
    main()

def multi_msg(message):
    """Prints given string message no matter where script is executed: in Python
    interpreter and ArcGIS geoprocessing dialog using
    print statement, also ArcGIS Results window (for background processing) or geoprocessing dialog using
    arcpy.AddMessage"""
    print(message)
    arcpy.AddMessage(message)

##def cleanup(intermediate_items_list):
##    """Safely deletes intermediate outputs using ArcGIS method only if they exist. Accepts a path expressed as a string or a list/tuple of paths. Uses ArcGIS existence test so geodatabase items are okay in addition to ordinary OS paths."""
##    if type(intermediate_items_list) is str:
##        intermediate_items_list = [intermediate_items_list]
##    for item in intermediate_items_list:
##        if arcpy.Exists(item):
##            try:
##                arcpy.Delete_management(item)
##            except Exception as e:
##                cu.multi_msg(e.message)
##                continue

##def directory_size(directory):
##    total_size = 0
##    for dirpath, dirnames, filenames in os.walk(directory):
##            for f in filenames:
##                f_abspath = os.path.join(dirpath, f)
##                total_size += os.path.getsize(f_abspath)
##    return float(total_size)

def merge_many(merge_list, out_fc, group_size = 20):
    """arcpy merge a list without blowing up your system
        this can be slow, but is usually better than the alternative
        if there are more than x (usually 20) files to merge, merge them in
        groups of 20 at a time to speed it up some"""
    if len(merge_list) > group_size:
        partitions = 1 + len(merge_list) // (group_size)
        multi_msg("Merging partition 1 of %s" % partitions)
        arcpy.Merge_management(merge_list[:group_size], out_fc)
        for n in range(2, partitions+1):
            multi_msg("Merging partition %s of %s" % (n, partitions))
            arcpy.Append_management(merge_list[group_size*(n-1):group_size*n], out_fc)
    else:
        arcpy.Merge_management(merge_list, out_fc)

def rename_field(inTable, oldFieldName, newFieldName, deleteOld = False):
    import arcpy
    old_field = arcpy.ListFields(inTable, oldFieldName)
    arcpy.AddField_management(inTable, newFieldName, old_field[0].type, field_length = old_field[0].length)
    arcpy.CalculateField_management(inTable, newFieldName,'!%s!' % oldFieldName, "PYTHON")
    if deleteOld == True: arcpy.DeleteField_management(inTable, oldFieldName)


def one_in_one_out(tool_table, zone_fc, zone_field, output_table):
    """ Occasionally, ArcGIS tools we use do not produce an output record for
    every input feature. This function is used in the toolbox whenever we need
    to correct this problem, and should be called at the end of the script to
    create the final output.
    tool_table: the intermediate table with missing features
    zone_fc: the feature class with the zones
    zone_field: the field uniquely identifying each feature that was used in
    the creation of tool_table. Because this function is called within our
    scripts, the zone_field should always be the same in tool_table and
    extent_fc
    output_table: the final output table
    """
    # get list of zones that need nulls inserted
    original_zones = {r[0] for r in arcpy.da.SearchCursor(zone_fc, zone_field)}
    null_zones = original_zones.difference({r[0] for r in arcpy.da.SearchCursor(tool_table, zone_field)})

    # get list of fields from table that can be inserted
    editable_fields = [f.name for f in arcpy.ListFields(tool_table) if f.editable]
    editable_fields.remove(zone_field)

    # insert a null row for every ID we identified
    iCursor = arcpy.da.InsertCursor(tool_table, [zone_field] + editable_fields)
    for zone_id in null_zones:
        new_row = [zone_id] + [None]*len(editable_fields)
        iCursor.insertRow(new_row)
    del iCursor

    # copy to output
    output_table = arcpy.CopyRows_management(tool_table, output_table)
    return output_table


def redefine_nulls(in_table, in_fields, out_values):
    """Sometimes, when a zone has nothing in it, it gets an output value of
    Null/NoData/None that we need to change to either a custom NA flag, or 0.
    in_table: the table that needs updating. It will be changed in place.
    in_fields: list of fields with null values that need updating
    out_values: a list the same length as in_fields, with the value to replace
    Null/NoData/None with.
    """
    arcpy.MakeTableView_management(in_table, 'table')
    for f, v in zip(in_fields, out_values):
        null_expr = '''"{0}" is null'''.format(f)
        arcpy.SelectLayerByAttribute_management('table', 'NEW_SELECTION', null_expr)
        calc_expr = """'{0}'""".format(v)
        arcpy.CalculateField_management('table', f, calc_expr, 'PYTHON')
    arcpy.Delete_management('table')

def resolution_comparison(feature_class, raster):
    """Compare the feature resolution to the raster resolution.
    Returns a value from 0-100 describing the percent of features that are
    larger than the area of one cell in the raster"""
    fc_count = int(arcpy.GetCount_management(feature_class).getOutput(0))

    # ask what the area of a cell in the raster is
    desc = arcpy.Describe(raster)
    cell_size = desc.meanCellHeight
    cell_area = desc.meanCellHeight * desc.meanCellWidth

    # ask what proportion of features are smaller than that
    small_count = 0
    with arcpy.da.SearchCursor(feature_class, ["SHAPE@AREA"]) as cursor:
        for row in cursor:
            if row[0] < cell_area:
                small_count += 1

    percent_ok = 100*(1 - (small_count/float(fc_count)))

    return((percent_ok))

def shortname(path):
    return os.path.splitext(os.path.basename(path))[0]

def create_temp_GDB(name):
    temp_dir = os.path.join(tempfile.gettempdir(), name)
    index = 0
    while os.path.exists(temp_dir):
        temp_dir = os.path.join(tempfile.gettempdir(), '{0}{1}'.format(name, index))
        index += 1
    os.mkdir(temp_dir)
    arcpy.CreateFileGDB_management(temp_dir, '{0}.gdb'.format(name))
    return(os.path.join(temp_dir,'{0}.gdb'.format(name)))

def lengthen_field(table_or_fc, field, new_length):
    old_field = arcpy.ListFields(table_or_fc, field)
    temp_field = 't_' + field
    arcpy.AddField_management(table_or_fc, temp_field, old_field[0].type, field_length = new_length)
    arcpy.CalculateField_management(table_or_fc, temp_field, '!{}!'.format(field), 'PYTHON')
    arcpy.DeleteField_management(table_or_fc, field)
    arcpy.AddField_management(table_or_fc, field, old_field[0].type, field_length = new_length)
    arcpy.CalculateField_management(table_or_fc, field, '!{}!'.format(temp_field), 'PYTHON')
    arcpy.DeleteField_management(table_or_fc, temp_field)



