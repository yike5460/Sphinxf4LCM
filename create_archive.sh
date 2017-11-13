#!/bin/bash
#
# Script for creating VNF Lifecycle Validation deployment archive 
# version 1.0: 13.11.2017
#

#### Parsing options

OPTS=`getopt -o vhns: --long source-dir:,twister-dir:,destination-dir:,help -n 'parse-options' -- "$@"`

function usage () {
    echo "Missing arguments: $1"
    echo "usage: create_archive --source-dir vnflcv_dir --twister-dir twister-dir --destination-dir destination_dir"
    echo "  vnflcv_dir        path where VNF LifeCycle Validation source files can be found"
    echo "  twister_dir       path where Twister source files are to be found"
    echo "  destination_dir   path where VNF LifeCycle Validation deployment archive will be created"
}

if [ $? != 0 ] ; then echo "Failed parsing options." >&2 ; exit 1 ; fi

eval set -- "$OPTS"

while true; do
  case "$1" in
    --source-dir ) VNFLCV_DIR=$2; shift; shift ;;
    --twister-dir ) TWISTER_DIR=$2; shift; shift ;;
    --destination-dir ) DESTINATION_DIR=$2; shift; shift ;;
    -h | --help ) usage "hai ca ma ca avem un argument"; exit 1;;
    * ) break ;;
    -- ) shift; break ;;
  esac
done

MISSING=""
if [ -z $VNFLCV_DIR ]; then
    MISSING="$MISSING --source-dir"
fi
if [ -z $TWISTER_DIR ]; then
    MISSING="$MISSING --twister-dir"
fi
if [ -z $DESTINATION_DIR ]; then
    MISSING="$MISSING --destination-dir"
fi
if [ ! -z "$MISSING" ]; then
    usage "$MISSING"
    exit 1
fi
echo VNFLCV_DIR=$VNFLCV_DIR
echo TWISTER_DIR=$TWISTER_DIR
echo DESTINATION_DIR=$DESTINATION_DIR

#### Creating structure for archive folder
echo "Creating structure for archive folder"
mkdir -p $DESTINATION_DIR/vnflcv/resources

#### Copying files in archive folder
echo "Copying files in archive folder"
cp -r $VNFLCV_DIR/deployment/conjure-up/spells/vnflcv/* $DESTINATION_DIR/vnflcv/
cp $VNFLCV_DIR/deployment/scripts/deploy.sh $DESTINATION_DIR/vnflcv/
cp $TWISTER_DIR/twister_demo.sql $DESTINATION_DIR/vnflcv/resources/
cp $TWISTER_DIR/twister_src.tar.gz $DESTINATION_DIR/vnflcv/resources/
echo "Creating VNF Lifecycle Validation source files archive"
cd $VNFLCV_DIR
tar czvf $DESTINATION_DIR/vnflcv/resources/vnflcv.tar.gz * > /dev/null 2>&1

#### Creating deployment archive
echo "Creating deployment archive"
cd $DESTINATION_DIR
tar czvf $DESTINATION_DIR/vnflcv.tar.gz vnflcv > /dev/null 2>&1
rm -rf $DESTINATION_DIR/vnflcv/

#### Done
echo "------------------------------------------------------"
echo "Done"
echo "VNF Lifecycle Management deployment archive created. You will find it in $DESTINATION_DIR/vnflcv.tar.gz"

