#!/usr/bin/env python3
"""Shared utilities for Cloudflare rulesets."""

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DataSize,
    DefaultValue,
    DictElement,
    Float,
    Integer,
    LevelDirection,
    SIMagnitude,
    SimpleLevels,
)


def simple_levels_percent(
    title: str,
    help_text: str,
    default_warn: float = 80.0,
    default_crit: float = 90.0,
) -> DictElement:
    """Create a SimpleLevels form for percentage values.

    Args:
        title: Form title
        help_text: Help text
        default_warn: Default warning threshold (percent)
        default_crit: Default critical threshold (percent)

    Returns:
        DictElement for the form
    """
    return DictElement(
        parameter_form=SimpleLevels(
            title=Title(title),
            help_text=Help(help_text),
            level_direction=LevelDirection.UPPER,
            form_spec_template=Float(unit_symbol="%"),
            prefill_fixed_levels=DefaultValue((default_warn, default_crit)),
        ),
        required=False,
    )


def simple_levels_float(
    title: str,
    help_text: str,
    unit: str = "",
    default_warn: float = 0.0,
    default_crit: float = 0.0,
) -> DictElement:
    """Create a SimpleLevels form for float values.

    Args:
        title: Form title
        help_text: Help text
        unit: Unit symbol
        default_warn: Default warning threshold
        default_crit: Default critical threshold

    Returns:
        DictElement for the form
    """
    return DictElement(
        parameter_form=SimpleLevels(
            title=Title(title),
            help_text=Help(help_text),
            level_direction=LevelDirection.UPPER,
            form_spec_template=Float(unit_symbol=unit) if unit else Float(),
            prefill_fixed_levels=DefaultValue((default_warn, default_crit)),
        ),
        required=False,
    )


def simple_levels_integer(
    title: str,
    help_text: str,
    unit: str = "",
    default_warn: int = 0,
    default_crit: int = 0,
) -> DictElement:
    """Create a SimpleLevels form for integer values.

    Args:
        title: Form title
        help_text: Help text
        unit: Unit symbol
        default_warn: Default warning threshold
        default_crit: Default critical threshold

    Returns:
        DictElement for the form
    """
    return DictElement(
        parameter_form=SimpleLevels(
            title=Title(title),
            help_text=Help(help_text),
            level_direction=LevelDirection.UPPER,
            form_spec_template=Integer(unit_symbol=unit) if unit else Integer(),
            prefill_fixed_levels=DefaultValue((default_warn, default_crit)),
        ),
        required=False,
    )


def simple_levels_milliseconds(
    title: str,
    help_text: str,
    default_warn: float = 0.0,
    default_crit: float = 0.0,
) -> DictElement:
    """Create a SimpleLevels form for millisecond values.

    Args:
        title: Form title
        help_text: Help text
        default_warn: Default warning threshold (ms)
        default_crit: Default critical threshold (ms)

    Returns:
        DictElement for the form
    """
    return simple_levels_float(
        title=title,
        help_text=help_text,
        unit="ms",
        default_warn=default_warn,
        default_crit=default_crit,
    )


def simple_levels_bytes(
    title: str,
    help_text: str,
    default_warn: int = 0,
    default_crit: int = 0,
) -> DictElement:
    """Create a SimpleLevels form for byte values.

    Args:
        title: Form title
        help_text: Help text
        default_warn: Default warning threshold (bytes)
        default_crit: Default critical threshold (bytes)

    Returns:
        DictElement for the form
    """
    return simple_levels_integer(
        title=title,
        help_text=help_text,
        unit="B",
        default_warn=default_warn,
        default_crit=default_crit,
    )


def simple_levels_datasize(
    title: str,
    help_text: str,
) -> DictElement:
    """Create a SimpleLevels form for data size with unit selector (Byte/KB/MB).

    Args:
        title: Form title
        help_text: Help text

    Returns:
        DictElement for the form with unit dropdown
    """
    return DictElement(
        parameter_form=SimpleLevels(
            title=Title(title),
            help_text=Help(help_text),
            level_direction=LevelDirection.UPPER,
            form_spec_template=DataSize(
                displayed_magnitudes=[
                    SIMagnitude.BYTE,
                    SIMagnitude.KILO,
                    SIMagnitude.MEGA,
                    SIMagnitude.GIGA,
                ],
            ),
            prefill_fixed_levels=DefaultValue((0, 0)),
        ),
        required=False,
    )


def simple_levels_lower_percent(
    title: str,
    help_text: str,
    default_warn: float = 20.0,
    default_crit: float = 10.0,
) -> DictElement:
    """Create a SimpleLevels form for lower percentage thresholds.

    Args:
        title: Form title
        help_text: Help text
        default_warn: Default warning threshold (percent)
        default_crit: Default critical threshold (percent)

    Returns:
        DictElement for the form
    """
    return DictElement(
        parameter_form=SimpleLevels(
            title=Title(title),
            help_text=Help(help_text),
            level_direction=LevelDirection.LOWER,
            form_spec_template=Float(unit_symbol="%"),
            prefill_fixed_levels=DefaultValue((default_warn, default_crit)),
        ),
        required=False,
    )


def simple_levels_lower_integer(
    title: str,
    help_text: str,
    unit: str = "",
    default_warn: int = 0,
    default_crit: int = 0,
) -> DictElement:
    """Create a SimpleLevels form for lower integer thresholds.

    Args:
        title: Form title
        help_text: Help text
        unit: Unit symbol
        default_warn: Default warning threshold
        default_crit: Default critical threshold

    Returns:
        DictElement for the form
    """
    return DictElement(
        parameter_form=SimpleLevels(
            title=Title(title),
            help_text=Help(help_text),
            level_direction=LevelDirection.LOWER,
            form_spec_template=Integer(unit_symbol=unit) if unit else Integer(),
            prefill_fixed_levels=DefaultValue((default_warn, default_crit)),
        ),
        required=False,
    )


def simple_levels_seconds(
    title: str,
    help_text: str,
    default_warn: int = 0,
    default_crit: int = 0,
) -> DictElement:
    """Create a SimpleLevels form for second values.

    Args:
        title: Form title
        help_text: Help text
        default_warn: Default warning threshold (seconds)
        default_crit: Default critical threshold (seconds)

    Returns:
        DictElement for the form
    """
    return simple_levels_integer(
        title=title,
        help_text=help_text,
        unit="s",
        default_warn=default_warn,
        default_crit=default_crit,
    )
