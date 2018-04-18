# Copyright 2017 The TensorFlow Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
"""Forward-mode derivatives."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from tensorflow.python.framework import ops
from tensorflow.python.ops import array_ops
from tensorflow.python.ops import control_flow_ops
from tensorflow.python.ops.gradients_impl import gradients


def fwd_gradients(ys, xs, grad_xs=None, assert_unused=False):
  """Computes forward-mode derivatives.

  This is accomplished in pure-python using tensorflow's existing (reverse-mode)
  gradients. There is additional overhead on graph construction, but runtime
  performance should be equal to a manual implementation [citation needed].

  See https://j-towns.github.io/2017/06/12/A-new-trick.html and
  https://github.com/HIPS/autograd/pull/175 for the original discussion of this
  method, and https://github.com/renmengye/tensorflow-forward-ad for a "direct"
  implementation.

  Args:
    ys: A list of tensors.
    xs: A list of tensors.
    grad_xs: An optional list of tensors. If provided, must have the same length
      and shapes compatible with xs.
    assert_unused: Add assertions that intermediate values are not computed.
  Returns:
    A list of tensors of the same shapes as ys. The directional derivatives of
    ys with respect to xs in the direction grad_xs. Leaving grad_xs unspecified
    is equivalent to passing in 1s for each x in xs.
  """
  # This version of forward-mode autodiff is based on code by Tim Cooijmans
  # and handles list arguments and certain special cases such as when the
  # ys doesn't depend on one or more of the xs, and when tf.IndexedSlices are
  # generated by the first tf.gradients call.

  us = [array_ops.zeros_like(y) + float('nan') for y in ys]

  dydxs = gradients(ys, xs, grad_ys=us)

  # deal with strange types that tf.gradients returns but can't deal with
  dydxs = [ops.convert_to_tensor(dydx) if isinstance(dydx, ops.IndexedSlices)
           else dydx for dydx in dydxs]

  if assert_unused:
    with ops.control_dependencies(dydxs):
      assert_unused = control_flow_ops.Assert(False, [1], name='fwd_gradients')
    with ops.control_dependencies([assert_unused]):
      dydxs = array_ops.identity_n(dydxs)

  dydxs = [array_ops.zeros_like(x) if dydx is None else dydx
           for x, dydx in zip(xs, dydxs)]
  for x, dydx in zip(xs, dydxs):
    dydx.set_shape(x.shape)

  dysdx = gradients(dydxs, us, grad_ys=grad_xs)

  return dysdx