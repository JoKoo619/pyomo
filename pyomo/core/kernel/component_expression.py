#  ___________________________________________________________________________
#
#  Pyomo: Python Optimization Modeling Objects
#  Copyright 2017 National Technology and Engineering Solutions of Sandia, LLC
#  Under the terms of Contract DE-NA0003525 with National Technology and
#  Engineering Solutions of Sandia, LLC, the U.S. Government retains certain
#  rights in this software.
#  This software is distributed under the 3-clause BSD License.
#  ___________________________________________________________________________

import sys

from pyomo.core.expr import expr_common
from pyomo.core.expr import current as EXPR
from pyomo.core.kernel.component_interface import \
    (IComponent,
     _abstract_readwrite_property,
     _abstract_readonly_property)
from pyomo.core.kernel.component_dict import ComponentDict
from pyomo.core.kernel.component_tuple import ComponentTuple
from pyomo.core.kernel.component_list import ComponentList

from pyomo.core.expr.numvalue import (NumericValue,
                                      is_fixed,
                                      is_constant,
                                      is_variable_type,
                                      potentially_variable,
                                      value,
                                      as_numeric)

import six

class IIdentityExpression(NumericValue):
    """The interface for classes that simply wrap another
    expression and perform no additional operations.

    Derived classes should declare an _expr attribute or
    override all implemented methods.
    """
    __slots__ = ()

    @property
    def expr(self):
        return self._expr

    #
    # Implement the NumericValue abstract methods
    #

    def __call__(self, exception=False):
        """Compute the value of this expression.

        Args:
            exception (bool): Indicates if an exception
                should be raised when instances of
                NumericValue fail to evaluate due to one or
                more objects not being initialized to a
                numeric value (e.g, one or more variables in
                an algebraic expression having the value
                None). Default is :const:`True`.

        Returns:
            numeric value or None
        """
        return value(self._expr, exception=exception)

    def is_constant(self):
        """A boolean indicating whether this expression is constant."""
        return is_constant(self._expr)

    def is_variable_type(self):
        """A boolean indicating whether this expression is a
        variable object."""
        return is_variable_type(self._expr)

    def is_fixed(self):
        """A boolean indicating whether this expression is fixed."""
        return is_fixed(self._expr)

    def is_potentially_variable(self):
        """A boolean indicating whether this expression can
        reference variables."""
        return potentially_variable(self._expr)

    def is_named_expression_type(self):
        """A boolean indicating whether this in a named expression."""
        return True

    def is_expression_type(self):
        """A boolean indicating whether this in an expression."""
        return True

    @property
    def _args_(self):
        """A tuple of subexpressions involved in this expressions operation."""
        return (self._expr,)

    @property
    def args(self):
        """A tuple of subexpressions involved in this expressions operation."""
        yield self._expr

    def nargs(self):
        """Length of self._nargs()"""
        return 1

    def arg(self, i):
        if i != 0:
            raise KeyError("Unexpected argument id")
        return self._expr

    def polynomial_degree(self):
        """The polynomial degree of the stored expression."""
        if self.is_fixed():
            return 0
        return self._expr.polynomial_degree()

    def _compute_polynomial_degree(self, values):
        return values[0]

    def to_string(self, verbose=None, labeler=None, smap=None, compute_values=False):
        """Convert this expression into a string."""
        return EXPR.expression_to_string(self, verbose=verbose, labeler=labeler, smap=smap, compute_values=compute_values)

    def _to_string(self, values, verbose, smap, compute_values):
        if verbose:
            name = self.getname()
            if name == None:
                return "<%s>{%s}" % (self.__class__.__name__, values[0])
            else:
                if name[0] == '<':
                    name = ""
                return "%s{%s}" % (name, values[0])
        if self._expr is None:
            return "%s{Undefined}" % str(self)
        return values[0]

    def _precedence(self):
        return 0

    def clone(self):
        raise NotImplementedError     #pragma:nocover

    def _apply_operation(self, result):
        return result[0]

    def _is_fixed(self, values):
        return values[0]

    def create_node_with_local_data(self, values):
        """
        Construct an expression after constructing the
        contained expression.

        This class provides a consistent interface for constructing a
        node, which is used in tree visitor scripts.
        """
        return self.__class__(expr=values[0])

class noclone(IIdentityExpression):
    """
    A helper factory class for creating an expression with
    cloning disabled. This allows the expression to be used
    in two or more parent expressions without causing a copy
    to be generated. If it is initialized with a value that
    is not an instance of NumericValue, that value is simply
    returned.
    """
    __slots__ = ("_expr",)

    def __new__(cls, expr):
        if isinstance(expr, NumericValue):
            return super(noclone, cls).__new__(cls)
        else:
            return expr

    def __init__(self, expr):
        self._expr = expr

    def __getnewargs__(self):
        return (self._expr,)

    def __getstate__(self):
        return (self._expr,)

    def __setstate__(self, state):
        assert len(state) == 1
        self._expr = state[0]

    def __str__(self):
        return "{%s}" % EXPR.expression_to_string(self)

    #
    # Ducktyping ExpressionBase functionality
    #

    def clone(self):
        """Return a clone of this expression (no-op)."""
        return self

class IExpression(IComponent, IIdentityExpression):
    """
    The interface for mutable expressions.
    """
    __slots__ = ()

    #
    # Implementations can choose to define these
    # properties as using __slots__, __dict__, or
    # by overriding the @property method
    #

    expr = _abstract_readwrite_property(
        doc="The stored expression")

    #
    # Override some of the NumericValue methods implemented
    # by the base class
    #

    def is_constant(self):
        """A boolean indicating whether this expression is constant."""
        return False

    def is_parameter_type(self):
        """A boolean indicating whether this expression is a parameter object."""
        return False

    def is_variable_type(self):
        """A boolean indicating whether this expression is a variable object."""
        return False

    def is_potentially_variable(self):
        """A boolean indicating whether this expression can
        reference variables."""
        return True

    #
    # Ducktyping ExpressionBase functionality
    #

    def clone(self):
        """Return a clone of this expression (no-op)."""
        return self

class expression(IExpression):
    """A named, mutable expression."""
    # To avoid a circular import, for the time being, this
    # property will be set externally
    _ctype = None
    __slots__ = ("_parent",
                 "_expr",
                 "__weakref__")
    def __init__(self, expr=None):
        self._parent = None
        self._expr = None

        # call the setter
        self.expr = expr

    #
    # Define the IExpression abstract methods
    #

    @property
    def expr(self):
        return self._expr
    @expr.setter
    def expr(self, expr):
        self._expr = expr

class data_expression(expression):
    """A named, mutable expression that is restricted to
    storage of data expressions. An exception will be raised
    if an expression is assigned that references (or is
    allowed to reference) variables."""
    __slots__ = ()

    #
    # Overload a few methods
    #

    def is_potentially_variable(self):
        """A boolean indicating whether this expression can
        reference variables."""
        return False

    def polynomial_degree(self):
        """Always return zero because we always validate
        that the stored expression can never reference
        variables."""
        return 0

    @property
    def expr(self):
        return self._expr
    @expr.setter
    def expr(self, expr):
        if potentially_variable(expr):
            raise ValueError("Expression is not restricted to data.")
        self._expr = expr

class expression_tuple(ComponentTuple):
    """A tuple-style container for expressions."""
    # To avoid a circular import, for the time being, this
    # property will be set externally
    _ctype = None
    __slots__ = ("_parent",
                 "_data")
    if six.PY3:
        # This has to do with a bug in the abc module
        # prior to python3. They forgot to define the base
        # class using empty __slots__, so we shouldn't add a slot
        # for __weakref__ because the base class has a __dict__.
        __slots__ = list(__slots__) + ["__weakref__"]

    def __init__(self, *args, **kwds):
        self._parent = None
        super(expression_tuple, self).__init__(*args, **kwds)

class expression_list(ComponentList):
    """A list-style container for expressions."""
    # To avoid a circular import, for the time being, this
    # property will be set externally
    _ctype = None
    __slots__ = ("_parent",
                 "_data")
    if six.PY3:
        # This has to do with a bug in the abc module
        # prior to python3. They forgot to define the base
        # class using empty __slots__, so we shouldn't add a slot
        # for __weakref__ because the base class has a __dict__.
        __slots__ = list(__slots__) + ["__weakref__"]

    def __init__(self, *args, **kwds):
        self._parent = None
        super(expression_list, self).__init__(*args, **kwds)

class expression_dict(ComponentDict):
    """A dict-style container for expressions."""
    # To avoid a circular import, for the time being, this
    # property will be set externally
    _ctype = None
    __slots__ = ("_parent",
                 "_data")
    if six.PY3:
        # This has to do with a bug in the abc module
        # prior to python3. They forgot to define the base
        # class using empty __slots__, so we shouldn't add a slot
        # for __weakref__ because the base class has a __dict__.
        __slots__ = list(__slots__) + ["__weakref__"]

    def __init__(self, *args, **kwds):
        self._parent = None
        super(expression_dict, self).__init__(*args, **kwds)
