import  sys
from    math import pi, degrees
import  operator

import  numpy as np
import  wx
from    wx import glcanvas

import  koko
from    koko.c.vec3f    import Vec3f
from    koko.c.libfab   import libfab
from    koko.fab.mesh   import Mesh

try:
    import OpenGL
    from OpenGL.GL      import *
    from OpenGL.arrays  import vbo
    from OpenGL.GL      import shaders
except ImportError:
    print 'kokopelli error: PyOpenGL import failed!'
    sys.exit(1)

################################################################################

class GLCanvas(glcanvas.GLCanvas):
    def __init__(self, parent, size=(500, 300)):
        glcanvas.GLCanvas.__init__(
            self, parent, wx.ID_ANY, size=size,
            style=glcanvas.WX_GL_DOUBLEBUFFER
        )
        self.context = glcanvas.GLContext(self)
        self.init = False

        self.Bind(wx.EVT_SIZE,       self.evt_size)
        self.Bind(wx.EVT_PAINT,      self.evt_paint)

        self.Bind(wx.EVT_LEFT_DOWN,  self.evt_mouse_left_down)
        self.Bind(wx.EVT_LEFT_UP,    self.evt_mouse_left_up)
        self.Bind(wx.EVT_MOTION,     self.evt_mouse_move)
        self.Bind(wx.EVT_MOUSEWHEEL, self.evt_mouse_scroll)

        self.mouse_spin = self.mouse_pan = False
        self.alpha = 0
        self.beta  = 0

        self.scale   = 1
        self._scale  = 1
        self.center  = Vec3f()
        self._center = Vec3f()

        self.meshes     = []
        self.mesh_vbos  = []
        self.leafs      = []

        self.path_vbo   = None

        self.image      = None

        self.loaded     = False
        self.snap       = True

        self.LOD_complete = False

################################################################################

    def clear(self):
        wx.CallAfter(self._clear)

    def _clear(self):
        self.meshes     = []
        self.mesh_vbos  = []
        self.path_vbo   = None
        self.image      = None
        self.Refresh()

    def clear_path(self):
        wx.CallAfter(self._clear_path)

    def _clear_path(self):
        self.path_vbo   = None
        self.Refresh()

    @property
    def texture(self):  return getattr(self, '_texture', None)
    @texture.setter
    def texture(self, value):
        if self.texture is not None:
            glDeleteTextures(self.texture)
        self._texture = value
        return self.texture
################################################################################

    @property
    def border(self):
        try:
            return self._border
        except AttributeError:
            self._border = None
            return self._border
    @border.setter
    def border(self, value):
        self._border = value
        wx.CallAfter(self.Refresh)


    def get_pixels(self):
        width, height = self.GetClientSize()
        glReadBuffer(GL_FRONT)
        glPixelStorei(GL_PACK_ALIGNMENT, 1)
        return width, height, glReadPixels(2, 2, width,height,
                                           GL_RGB, GL_UNSIGNED_BYTE)

################################################################################

    def evt_size(self, evt=None):
        if not self.init:
            self.init_GL()
        else:
            self.update_viewport()

################################################################################

    def evt_paint(self, evt=None, shader=None):
        if not self.init:
            self.init_GL()
        self.draw(shader)

################################################################################

    def evt_mouse_left_down(self, evt):
        self.mouse = wx.Point(evt.GetX(), evt.GetY())
        if wx.GetKeyState(wx.WXK_SHIFT):
            self.mouse_pan  = True
        else:
            self.mouse_spin = True

################################################################################

    def evt_mouse_left_up(self, evt):
        self.mouse_spin = self.mouse_pan = False

################################################################################

    def evt_mouse_move(self, evt):
        pos = wx.Point(evt.GetX(), evt.GetY())
        if self.mouse_spin:
            delta = pos - self.mouse
            self.alpha = (self.alpha + delta.x) % 360
            self.beta  -= delta.y
            if   self.beta < 0: self.beta = 0
            elif self.beta > 180: self.beta = 180
            self.Refresh()
        elif self.mouse_pan:
            delta = pos - self.mouse
            delta = Vec3f(0.01/self.scale*delta.x, -0.01/self.scale*delta.y, 0)
            proj = delta.deproject(self.alpha, self.beta)
            self.center.x -= proj.x
            self.center.y -= proj.y
            self.center.z -= proj.z
            self.Refresh()
        self.LOD_complete = False
        self.mouse = pos

################################################################################

    def evt_mouse_scroll(self, evt):
        if wx.GetKeyState(wx.WXK_SHIFT):
            delta = Vec3f(0, 0, 0.01*evt.GetWheelRotation()/self.scale)
            proj = delta.deproject(self.alpha, self.beta)
            self.center.x -= proj.x
            self.center.y -= proj.y
            self.center.z -= proj.z
        else:
            dScale = 1 / 1.0025 if evt.GetWheelRotation() < 0 else 1.0025
            for i in range(abs(evt.GetWheelRotation())):
                self.scale *= dScale
        self.LOD_complete = False
        self.Refresh()

################################################################################

    def update_viewport(self):
        self.SetCurrent(self.context)
        w, h = self.Size
        glViewport(0, 0, w, h)

        glMatrixMode(GL_PROJECTION)
        glLoadIdentity();

        aspect = w/float(h)

        if aspect > 1:  glFrustum(-aspect, aspect, -1, 1, 1, 9)
        else:           glFrustum(-1, 1, -1/aspect, 1/aspect, 1, 9)

        glMatrixMode(GL_MODELVIEW)

################################################################################

    def compile_shaders(self):

        mesh_vs = """
            #version 120
            attribute vec3 vertex_position;
            attribute vec3 vertex_normal;

            varying vec3 normal;

            void main() {
                gl_Position = gl_ModelViewProjectionMatrix *
                              vec4(vertex_position, 1.0);

                normal = normalize(gl_NormalMatrix*vertex_normal);
            }
        """
        shaded_fs = """
            #version 120

            varying vec3 normal;
            uniform vec4 color;

            void main() {
                gl_FragColor = vec4(0.1+0.9*normal[2]*color[0],
                                    0.1+0.9*normal[2]*color[1],
                                    0.1+0.9*normal[2]*color[2],
                                    color[3]);
            }
        """

        wire_fs = """
            #version 120

            varying vec3 normal;
            uniform vec4 color;

            void main() {
                float B = normal[2] < 0 ? 0.2 : normal[2]*0.8+0.2;
                gl_FragColor = vec4(B*color[0], B*color[1], B*color[2], color[3]);
            }
        """
        norm_fs = """
            #version 120

            varying vec3 normal;

            void main() {
                gl_FragColor = vec4(normal[0]/2+0.5,
                                    normal[1]/2+0.5,
                                    normal[2]/2+0.5, 1 );
            }
        """


        self.plain_shader = shaders.compileProgram(
            shaders.compileShader(mesh_vs,      GL_VERTEX_SHADER),
            shaders.compileShader(shaded_fs,    GL_FRAGMENT_SHADER))
        self.wire_shader = shaders.compileProgram(
            shaders.compileShader(mesh_vs,      GL_VERTEX_SHADER),
            shaders.compileShader(wire_fs,      GL_FRAGMENT_SHADER))
        self.norm_shader = shaders.compileProgram(
            shaders.compileShader(mesh_vs,      GL_VERTEX_SHADER),
            shaders.compileShader(norm_fs,      GL_FRAGMENT_SHADER))

        flat_vs = """
            #version 120
            attribute vec3 vertex_position;

            void main() {
                gl_Position = gl_ModelViewProjectionMatrix *
                              vec4(vertex_position, 1.0);
            }
        """
        flat_fs = """
            #version 120

            uniform vec4 color;

            void main() {
                gl_FragColor = color;
            }
        """


        self.flat_shader = shaders.compileProgram(
            shaders.compileShader(flat_vs,      GL_VERTEX_SHADER),
            shaders.compileShader(flat_fs,      GL_FRAGMENT_SHADER))

        path_vs = """
            #version 120
            attribute vec3  vertex_position;
            attribute float vertex_color;

            varying float color;

            void main() {
                gl_Position = gl_ModelViewProjectionMatrix *
                              vec4(vertex_position, 1.0);
                color = vertex_color;
            }
        """

        path_fs = """
            #version 120

            varying float color;
            uniform int show_traverses;

            void main() {
                if (color == 0)
                    gl_FragColor = vec4(0.9, 0.2, 0.2,
                                        show_traverses > 0 ? 0.5 : 0);
                else
                    gl_FragColor = vec4(0.3*color+0.2,
                                        0.8*color+0.2,
                                        (1-color),
                                        0.9);
            }
        """
        self.path_shader = shaders.compileProgram(
            shaders.compileShader(path_vs, GL_VERTEX_SHADER),
            shaders.compileShader(path_fs, GL_FRAGMENT_SHADER))

        tex_vs = """
            #version 120

            attribute vec3 vertex_position;
            attribute vec2 vertex_texcoord;

            varying vec2 texcoord;

            void main()
            {
                gl_Position = gl_ModelViewProjectionMatrix *
                              vec4(vertex_position, 1.0);
                texcoord = vertex_texcoord;
            }
        """
        tex_fs = """
            #version 120

            uniform sampler2D texture;
            varying vec2 texcoord;

            void main()
            {
                vec4 color = texture2D(texture, texcoord);
                if (color[0] != 0 || color[1] != 0 || color[2] != 0)
                    gl_FragColor = color;
                else
                    gl_FragColor = vec4(0, 0, 0, 0);
            }
        """
        self.image_shader = shaders.compileProgram(
            shaders.compileShader(tex_vs, GL_VERTEX_SHADER),
            shaders.compileShader(tex_fs, GL_FRAGMENT_SHADER)
        )

################################################################################

    def init_GL(self):
        self.SetCurrent(self.context)
        self.compile_shaders()

        glEnable(GL_DEPTH_TEST)

        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        self.update_viewport()

        self.init = True

################################################################################

    def load_mesh(self, mesh):
        self.load_meshes([mesh])

    def load_meshes(self, meshes):
        ''' Loads a ctypes array of floats into a vertex buffer object. '''

        # Find useful parameters about the mesh.
        min_corner = Vec3f(min(m.X.lower for m in meshes),
                           min(m.Y.lower for m in meshes),
                           min(m.Z.lower for m in meshes))
        max_corner = Vec3f(max(m.X.upper for m in meshes),
                           max(m.Y.upper for m in meshes),
                           max(m.Z.upper for m in meshes))
        center = (min_corner + max_corner) / 2

        L = (min_corner - center).length()
        scale = 4/L

        wx.CallAfter(self._load_meshes, meshes, scale, center)

    def _load_meshes(self, meshes, scale, center):
        self.meshes     = meshes
        self._scale = scale
        self._center = center

        if self.snap:
            self.snap_bounds()
            self.snap = False

        self.reload_vbos()


################################################################################

    def reload_vbos(self):
        mesh_vbos = []

        # Each mesh gets its own VBO.
        # Each leaf gets its own unique color within the mesh VBO

        all_leafs = []
        for m in self.meshes:
            leafs = m.leafs()
            all_leafs += leafs
            merged = Mesh.merge(leafs)

            tcounts = [L.tcount for L in leafs]

            mesh_vbos.append(
                (vbo.VBO(merged.vdata, size=merged.vcount*4*6),
                 vbo.VBO(merged.tdata, target=GL_ELEMENT_ARRAY_BUFFER,
                     size=merged.tcount*4*3),
                 tcounts,
                 m, merged)
            )


        wx.CallAfter(self._reload_vbos, mesh_vbos, all_leafs)


    def _reload_vbos(self, mesh_vbos, leafs):
        self.mesh_vbos  = mesh_vbos
        self.leafs      = leafs
        self.Refresh()


################################################################################

    def load_paths(self, paths, xmin, ymin, zmin):
        count = sum(map(lambda p: len(p.points)+p.closed+2, paths))
        vdata = (ctypes.c_float*(count*4))()

        xyz = lambda pt: [pt[0]+xmin, pt[1]+ymin, pt[2]+zmin]

        vindex = 0
        for p in paths:
            vdata[vindex:vindex+4] = xyz(p.points[0]) + [0]
            vindex += 4

            for pt in p.points:
                vdata[vindex:vindex+4] = \
                    xyz(pt) + [0.1+0.9*vindex/float(len(vdata))]
                vindex += 4

            # Close the path
            if p.closed:
                vdata[vindex:vindex+4] = \
                    xyz(p.points[0]) + [0.1+0.9*vindex/float(len(vdata))]
                vindex += 4

            vdata[vindex:vindex+4] = xyz(p.points[-1]) + [0]
            vindex += 4

        path_vbo = vbo.VBO(vdata)
        wx.CallAfter(self._load_paths, path_vbo)

    def _load_paths(self, path_vbo):
        self.path_vbo = path_vbo
        self.Refresh()

################################################################################

    def load_images(self, images):
        wx.CallAfter(self._load_image, images[0].__class__.merge(images))

    def load_image(self, image):
        wx.CallAfter(self._load_image, image)

    def _load_image(self, image):

        image = image.copy(depth=8, channels=3)
        data = np.flipud(image.array)

        self.tex_vbo = vbo.VBO((ctypes.c_float*30)(
            image.xmin, image.ymin, 0, 0, 0,
            image.xmax, image.ymin, 0, 1, 0,
            image.xmax, image.ymax, 0, 1, 1,

            image.xmin, image.ymin, 0, 0, 0,
            image.xmax, image.ymax, 0, 1, 1,
            image.xmin, image.ymax, 0, 0, 1
        ))

        self.texture = glGenTextures(1)
        self.image = image

        glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
        glBindTexture(GL_TEXTURE_2D, self.texture)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, image.width, image.height, 0,
                     GL_RGB, GL_UNSIGNED_BYTE, data.flatten())

        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)

        corner = Vec3f(image.xmin, image.ymin, 0)
        self._center = corner + Vec3f(image.dx, image.dy, 0)/2
        self._scale = 4/(Vec3f(image.dx, image.dy, 0)/2).length()

################################################################################

    def draw(self, shader=None):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        shading = koko.FRAME.get_menu('View', 'Shading mode')
        shader = [c.GetLabel() for c in shading if c.IsChecked()][0]

        if shader == 'Show subdivision':
            self.draw_flat(50)
        else:
            self.draw_mesh(shader)

        if self.path_vbo is not None:
            self.draw_paths()

        if self.image is not None:
            self.draw_image()

        if self.border is not None:
            self.draw_border()

        self.SwapBuffers()

################################################################################

    def draw_mesh(self, shader):

        if shader == 'Show wireframe':
            glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
        else:
            glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)

        glPushMatrix()
        self.orient()

        current_shader = {'Wireframe': self.wire_shader,
                          'Normals':   self.norm_shader,
                          'Shaded':    self.plain_shader}[shader]

        shaders.glUseProgram(current_shader)

        # Find the positions of shader attributes
        attributes = {}
        for a in ['vertex_position', 'vertex_normal']:
            attributes[a] = glGetAttribLocation(current_shader, a)
            glEnableVertexAttribArray(attributes[a])

        color_loc = glGetUniformLocation(current_shader, 'color')

        # Loop over meshes
        for vertex_vbo, index_vbo, tcounts, _, mesh in self.mesh_vbos:
            vertex_vbo.bind()
            index_vbo.bind()

            (r,g,b) = mesh.color if mesh.color else (255, 255, 255)

            if color_loc != -1:
                glUniform4f(color_loc, r/255., g/255., b/255., 1)

            glVertexAttribPointer(
                attributes['vertex_position'], # attribute index
                3,                     # number of components per attribute
                GL_FLOAT,              # data type of each component
                False,                 # Do not normalize components
                6*4,                   # stride length (in bytes)
                vertex_vbo)            # Vertex buffer object

            glVertexAttribPointer(
                attributes['vertex_normal'], 3,
                GL_FLOAT, False, 6*4, vertex_vbo + 12)

            # Draw the triangles stored in the vbo
            glDrawElements(GL_TRIANGLES, sum(tcounts)*3,
                           GL_UNSIGNED_INT, index_vbo)


            index_vbo.unbind()
            vertex_vbo.unbind()

        for a in attributes.itervalues():   glDisableVertexAttribArray(a)

        shaders.glUseProgram(0)

        # Draw bounds and axes if the appropriate menu items are checked
        if koko.FRAME.get_menu('View', 'Show bounds').IsChecked():
            self.draw_bounds()
        if koko.FRAME.get_menu('View', 'Show axes').IsChecked():
            self.draw_axes()

        glPopMatrix()

################################################################################

    def sample(self):

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        self.draw_flat()

        width, height = self.GetClientSize()
        glReadBuffer(GL_BACK)
        glPixelStorei(GL_PACK_ALIGNMENT, 1)
        pixels = glReadPixels(
            2, 2, width,height, GL_RGB, GL_UNSIGNED_BYTE
        )

        count = (ctypes.c_uint32*len(self.leafs))()
        libfab.count_by_color(
            ctypes.c_char_p(pixels), width, height, len(self.leafs), count
        )

        out = {}
        for c, m in zip(count, self.leafs):
            out[m] = c/float(width*height)
        return out


    def draw_flat(self, scale=1):

        glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)

        glPushMatrix()
        self.orient()

        shaders.glUseProgram(self.flat_shader)

        # Find the positions of shader attributes
        attributes = {}
        vertex_loc = glGetAttribLocation(self.flat_shader, 'vertex_position')
        glEnableVertexAttribArray(vertex_loc)
        color_loc = glGetUniformLocation(self.flat_shader, 'color')

        # Loop over meshes
        index = 1
        for vertex_vbo, index_vbo, tcounts, _, mesh in self.mesh_vbos:

            vertex_vbo.bind()
            index_vbo.bind()

            glVertexAttribPointer(
                vertex_loc,            # attribute index
                3,                     # number of components per attribute
                GL_FLOAT,              # data type of each component
                False,                 # Do not normalize components
                6*4,                   # stride length (in bytes)
                vertex_vbo)            # Vertex buffer object


            # Draw leafs from the VBO, with each leaf getting
            # its own unique color.
            offset = 0
            for tcount in tcounts:
                i = index
                b = (i % (256/scale))
                i /= 256/scale
                g = (i % (256/scale))
                i /= 256/scale
                r = (i % (256/scale))
                index += 1

                glUniform4f(
                    color_loc, r/(256./scale), g/(256./scale),
                    b/(256./scale), 1
                )

                glDrawElements(
                    GL_TRIANGLES, tcount*3,
                    GL_UNSIGNED_INT, index_vbo + offset
                )
                offset += tcount*4*3


            index_vbo.unbind()
            vertex_vbo.unbind()

        glDisableVertexAttribArray(vertex_loc)

        shaders.glUseProgram(0)

        glPopMatrix()

################################################################################

    def draw_axes(self):
        glDisable(GL_DEPTH_TEST)
        glScalef(0.5/self.scale, 0.5/self.scale, 0.5/self.scale)
        glLineWidth(2)
        glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
        glBegin(GL_LINES)
        glColor3f(1, 0, 0)
        glVertex3f(0, 0, 0)
        glVertex3f(1, 0, 0)
        glColor3f(0, 1, 0)
        glVertex3f(0, 0, 0)
        glVertex3f(0, 1, 0)
        glColor3f(0.2, 0.2, 1)
        glVertex3f(0, 0, 0)
        glVertex3f(0, 0, 1)
        glEnd()
        glLineWidth(1)
        glEnable(GL_DEPTH_TEST)

################################################################################

    def draw_cube(self, X, Y, Z):
        glBegin(GL_QUADS)
        for z in (Z.upper, Z.lower):
            glVertex(X.lower, Y.lower, z)
            glVertex(X.lower, Y.upper, z)
            glVertex(X.upper, Y.upper, z)
            glVertex(X.upper, Y.lower, z)
        for y in (Y.upper, Y.lower):
            glVertex(X.lower, y, Z.lower)
            glVertex(X.lower, y, Z.upper)
            glVertex(X.upper, y, Z.upper)
            glVertex(X.upper, y, Z.lower)
        for x in (X.lower, X.upper):
            glVertex(x, Y.lower, Z.lower)
            glVertex(x, Y.lower, Z.upper)
            glVertex(x, Y.upper, Z.upper)
            glVertex(x, Y.upper, Z.lower)
        glEnd()

    def draw_rect(self, X, Y):
        glBegin(GL_QUADS)
        glVertex(X[0], Y[0], 0)
        glVertex(X[1], Y[0], 0)
        glVertex(X[1], Y[1], 0)
        glVertex(X[0], Y[1], 0)
        glEnd()

    def draw_bounds(self):
        glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
        glColor3f(0.5, 0.5, 0.5)
        for m in self.meshes:
            self.draw_cube(m.X, m.Y, m.Z)
        if self.image:
            self.draw_rect(
                (self.image.xmin, self.image.xmax),
                (self.image.ymin, self.image.ymax)
            )



################################################################################

    def draw_border(self):
        ''' Draws a colored border around the edge of the screen. '''
        glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)

        w, h = self.Size
        glViewport(0, 0, w, h)

        aspect = w/float(h)

        if aspect > 1:
            xmin, xmax = -aspect, aspect
            ymin, ymax = -1, 1
        else:
            xmin, xmax = -1, 1
            ymin, ymax = -1/aspect, 1/aspect

        glBegin(GL_QUADS)
        glColor3f(self.border[0]/255.,
                  self.border[1]/255.,
                  self.border[2]/255.)

        glVertex(xmin, ymin, -1)
        glVertex(xmin, ymax, -1)
        glVertex(xmin+0.01, ymax, -1)
        glVertex(xmin+0.01, ymin, -1)

        glVertex(xmin, ymax, -1)
        glVertex(xmax, ymax, -1)
        glVertex(xmax, ymax-0.01, -1)
        glVertex(xmin, ymax-0.01, -1)

        glVertex(xmax-0.01, ymin, -1)
        glVertex(xmax-0.01, ymax, -1)
        glVertex(xmax, ymax, -1)
        glVertex(xmax, ymin, -1)

        glVertex(xmin, ymin+0.01, -1)
        glVertex(xmax, ymin+0.01, -1)
        glVertex(xmax, ymin, -1)
        glVertex(xmin, ymin, -1)

        glEnd()

################################################################################

    def draw_image(self):

        glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)

        glPushMatrix()

        self.orient()

        # Set up various parameters
        shaders.glUseProgram(self.image_shader)
        attributes = {}
        for a in ['vertex_position', 'vertex_texcoord']:
            attributes[a] = glGetAttribLocation(self.image_shader, a)
            glEnableVertexAttribArray(attributes[a])

        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, self.texture)
        glUniform1i(
            glGetUniformLocation(self.image_shader, 'texture'), 0
        )

        self.tex_vbo.bind()
        glVertexAttribPointer(
            attributes['vertex_position'],
            3, GL_FLOAT, False, 5*4, self.tex_vbo
        )
        glVertexAttribPointer(
            attributes['vertex_texcoord'],
            2, GL_FLOAT, False, 5*4, self.tex_vbo+3*4
        )


        glDrawArrays(GL_TRIANGLES,  0, 6)

        # And disable all of those parameter
        for a in attributes.itervalues():   glDisableVertexAttribArray(a)

        self.tex_vbo.unbind()
        shaders.glUseProgram(0)

        glPopMatrix()

################################################################################

    def draw_paths(self):
        glLineWidth(2)

        glPushMatrix()

        self.orient()

        current_shader = self.path_shader
        shaders.glUseProgram(current_shader)

        self.path_vbo.bind()

        # Find the positions of shader attributes
        attributes = {}
        for a in ['vertex_position', 'vertex_color']:
            attributes[a] = glGetAttribLocation(current_shader, a)
            glEnableVertexAttribArray(attributes[a])

        # Set vertex attribute pointers
        glVertexAttribPointer(
            attributes['vertex_position'], 3,
            GL_FLOAT, False, 4*4, self.path_vbo)

        glVertexAttribPointer(
            attributes['vertex_color'], 1,
            GL_FLOAT, False, 4*4, self.path_vbo + 12)

        # Show or hide traverses
        t = koko.FRAME.get_menu('View','Show traverses').IsChecked()
        glUniform1i(
            glGetUniformLocation(current_shader, 'show_traverses'),
            1 if t else 0
        )

        # Draw the triangles stored in the vbo
        glDrawArrays(GL_LINE_STRIP, 0, len(self.path_vbo)/4)

        for a in attributes.itervalues():   glDisableVertexAttribArray(a)

        self.path_vbo.unbind()

        shaders.glUseProgram(0)

        glPopMatrix()
        glLineWidth(1)

################################################################################

    def orient(self):
        glTranslatef(0, 0, -5)
        glScalef(self.scale, self.scale, self.scale)
        glRotatef(-self.beta,  1, 0, 0)
        glRotatef(self.alpha, 0, 0, 1)
        glTranslatef(-self.center.x, -self.center.y, -self.center.z)

    def snap_bounds(self):
        ''' Snap to saved center and model scale. '''
        self.center = self._center.copy()
        self.scale  = self._scale
        self.Refresh()

    def snap_axis(self, axis):
        ''' Snaps to view along a particular axis. '''

        if axis == '+x':
            self.alpha, self.beta = 90, 90
        elif axis == '+y':
            self.alpha, self.beta = 0, 90
        elif axis == '+z':
            self.alpha, self.beta = 0, 0
        elif axis == '-x':
            self.alpha, self.beta = 270, 90
        elif axis == '-y':
            self.alpha, self.beta = 180, 90
        elif axis == '-z':
            self.alpha, self.beta = 0, 180
        self.Refresh()
