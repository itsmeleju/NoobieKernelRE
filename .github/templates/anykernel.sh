# AnyKernel3 Ramdisk Mod Script
# Fallback template, used only when the repo has no AnyKernel3/anykernel.sh.
# Check BLOCK and the device names against your A32 before flashing.

## AnyKernel setup
# begin properties
properties() { '
kernel.string=NoobieKernelRE
do.devicecheck=1
do.modules=0
do.systemless=0
do.cleanup=1
do.cleanuponabort=0
device.name1=a32
device.name2=A325F
device.name3=a32nsxx
device.name4=
device.name5=
supported.versions=
supported.patchlevels=
supported.vendorpatchlevels=
'; } # end properties

### AnyKernel install
## boot files attributes
boot_attributes() {
set_perm_recursive 0 0 755 644 $RAMDISK/*;
set_perm_recursive 0 0 750 750 $RAMDISK/init* $RAMDISK/sbin;
} # end attributes

# boot shell variables
BLOCK=/dev/block/by-name/boot;
IS_SLOT_DEVICE=0;
RAMDISK_COMPRESSION=auto;
PATCH_VBMETA_FLAG=auto;

# import functions/variables and setup patching - see for reference (DO NOT REMOVE)
. tools/ak3-core.sh;

# boot install
dump_boot;
write_boot;
## end boot install
