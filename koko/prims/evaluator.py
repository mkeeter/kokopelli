import re

import koko

class Evaluator(object):
    '''Class to do lazy evaluation of expressions.'''

    def __init__(self, expr, out):
        self.type   = out
        self._expr  = str(expr)

        # Add a default value for self.result
        self.recursing  = False
        self.cached     = False

        self.result = out() if out is not None else None
        self.eval()

    def eval(self):
        '''Evaluate the given expression.

           Sets self.valid to True or False depending on whether the
           evaluation succeeded.'''

        if self.cached: return self.result

        # Prevent recursive loops (e.g. defining pt0.x = pt0.x)
        if self.recursing:
            self.valid = False
            raise RuntimeError('Bad recursion')

        # Set a few local variables
        self.recursing  = True
        self.valid      = True

        try:
            c = eval(self._expr, {}, koko.PRIMS.map)
        except:
            self.valid = False
        else:
            # If we have a desired type and we got something else,
            # try to coerce the returned value into the desired type
            if self.type is not None and not isinstance(c, self.type):
                try:    c = self.type(c)
                except: self.valid = False

            # Make sure that we haven't ended up invalid
            # due to bad recursion somewhere down the line
            if self.valid: self.result = c

        # We're no longer recursing, so we can unflag the variable
        self.recursing = False

        return self.result

    @property
    def expr(self):
        return self._expr
    @expr.setter
    def expr(self, value):
        self.set_expr(value)
    def set_expr(self, value):
        new = str(value)
        old = self._expr
        self._expr = new
        if new != old:
            self.cached = False
            koko.APP.mark_changed_design()
            koko.PRIMS.update_panels()

################################################################################

class NameEvaluator(Evaluator):
    '''Class to store valid variable names.'''
    def __init__(self, expr):
        Evaluator.__init__(self, expr, str)

    def eval(self):
        ''' Check to see that the expression is a valid variable name
            and return it.'''
        if self.cached: return self.result

        if self.valid_regex.match(self.expr):
            self.valid = True
            self.result = self.expr
        else:
            self.valid = False
        self.cached = True
        return self.result


    valid_regex = re.compile('[a-zA-Z_][0-9a-zA-Z_]*$')
