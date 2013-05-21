""" Module containing input modules.

    Each input module must define TYPE (the python type of the desired input)
    and WORKFLOWS (a dictionary mapping different panel types to workflows
    that lead to that type of panel).
"""
import asdf, cad, image

INPUTS = [asdf, cad, image]
