# Copyright (C) 2015 MediaTek Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#

obj-y += ged/
obj-y += hal/

# Conditional GPU Driver Selection (Kconfig options for Noobie-defconfig)
ifeq ($(CONFIG_MTK_GPU_MALI_R25P),y)
    obj-y += gpu_mali/mali_bifrost/mali-r25p0/drivers/gpu/arm/midgard/
else ifeq ($(CONFIG_MTK_GPU_MALI_R32P),y)
    obj-y += gpu_mali/mali_valhall/mali-r32p1/drivers/gpu/arm/midgard/
else
    # Legacy MediaTek GPU Selection Fallback
    MTK_GPU_VERSION = $(subst ",,$(CONFIG_MTK_GPU_VERSION))
    $(info MTK_GPU_VERSION 1 = $(word 1,$(MTK_GPU_VERSION)))

    ifeq ($(CONFIG_MTK_GPU_R5P0),y)
        obj-y += $(subst ",,$(CONFIG_MTK_PLATFORM))/
    else ifeq ($(CONFIG_MACH_MT6781),y)
        $(info *direct build mali-r32p1 for CONFIG_MACH_MT6781)
        obj-y += gpu_mali/mali_valhall/mali-r32p1/drivers/gpu/arm/midgard/
    else ifneq ($(word 1,$(MTK_GPU_VERSION)),)
        obj-y += gpu_$(word 1,$(MTK_GPU_VERSION))/
    else
        obj-y += $(subst ",,$(CONFIG_MTK_PLATFORM))/
    endif
endif

# MediaTek Buffer Manager (gpu_bm) rules
ifneq (,$(filter $(CONFIG_MTK_PLATFORM), "mt6785"))
    obj-y += gpu_bm/
endif

obj-$(CONFIG_MACH_MT6885) += gpu_bm/
obj-$(CONFIG_MACH_MT6893) += gpu_bm/
obj-$(CONFIG_MACH_MT6873) += gpu_bm/
obj-$(CONFIG_MACH_MT6853) += gpu_bm/
obj-$(CONFIG_MACH_MT6833) += gpu_bm/
obj-$(CONFIG_MACH_MT6877) += gpu_bm/
obj-$(CONFIG_MACH_MT6781) += gpu_bm/
