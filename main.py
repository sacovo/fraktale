# Main File
from gi.repository import Gtk, GObject
GObject.threads_init()
import matplotlib
matplotlib.use('Agg')
from matplotlib.figure import Figure
from matplotlib.backends.backend_gtk3agg import FigureCanvasGTK3Agg as FigureCanvas
from matplotlib.backends.backend_gtk3 import NavigationToolbar2GTK3 as NavigationToolbar
from matplotlib import cm, pylab, rc
import numpy as np
from numpy import *
from threading import Thread
from turtle import Turtle
pylab.hold(False)

from pkg_resources import resource_string

import os

class Pen:
    def __init__(self, canvas, commands):
        self.canvas = canvas
        self.commands = {}
        self.segments = []
        self.angle = 0
        for line in commands.split('\n'):
            c, cmd = [x.strip() for x in line.split(':')]
            method, arg = [x.strip() for x in cmd.split(' ')]
            self.commands[c] = (method, arg)

        self.cdict = {
                'forward': self.forward,
                'backward': self.backward,
                'rotate': self.rotate,
                'move': self.move,
                'nothing': self.nothing,
                'store': self.store_,
                'pop': self.pop,
                }
        self.store = []
        self.x = 0
        self.y = 0

    def move(self, dis):
        x, y = self.x, self.y
        xn = x + dis*np.cos(self.get_rad())
        yn = y + dis*np.sin(self.get_rad())
        self.x = xn
        self.y = yn

    def exec_str(self, string):
        for c in string:
            self.exec_cmd(c)

    def store_(self, cmd):
        self.store.append((self.x, self.y, self.angle))
    
    def pop(self, cmd):
        self.x, self.y, self.angle = self.store.pop()

    def nothing(self, cmd):
        pass

    def exec_cmd(self, cmd):
        method = self.commands[cmd]
        self.cdict[method[0]](int(method[1]))

    def forward(self, dis=10):
        x, y = self.x, self.y
        xn = x + dis*np.cos(self.get_rad())
        yn = y + dis*np.sin(self.get_rad())
        self.segments.append(((x, y), (xn,yn)))
        self.x = xn
        self.y = yn

    def backward(self, dis=10):
        x, y = self.x, self.y
        xn = x - dis*np.cos(self.get_rad())
        yn = y - dis*np.sin(self.get_rad())
        self.segments.append(((x,y), (xn,yn)))
        self.x = xn
        self.y = yn

    def get_rad(self):
        return self.angle * (np.pi/180)
    
    def rotate(self, angle=60):
        self.angle += angle
        self.angle = self.angle % 360

class LSystem:
    def __init__(self, axiom, s):
        self.axiom = axiom
        rules = {} 
        for rule in s.split(sep=','):
            left, right = [x.strip() for x in rule.split(sep='->')]
            rules[left] = right
        self.rules = rules
        self.string = axiom
        self.generation = 0

    def next_gen(self):
        new_string = ''

        i = 0
        while i < len(self.string):
            for key, value in self.rules.items():
                if self.string[i:i+len(key)]==key:
                    new_string += value
                    i += len(key)
                    break
            else:
                new_string+=self.string[i]
                i += 1
        new_string = new_string
        self.string = new_string
        self.generation += 1
        return new_string



class Main:
    def __init__(self):
        builder = Gtk.Builder()
        builder.add_from_string(resource_string(__name__, 'gui.glade').decode())
        builder.connect_signals(self)

        self.window = builder.get_object("window")
        
        self.figure = Figure(figsize=(100,250), dpi=75)
        self.axis = self.figure.add_subplot(111)
        self.canvas = FigureCanvas(self.figure)

        self.toolbar = NavigationToolbar(self.canvas, self.window)

        imbox = builder.get_object("image_box")
        imbox.pack_start(self.toolbar, False, False, 1)
        imbox.pack_start(self.canvas, True, True, 1)
        self.progress = builder.get_object("progressbar")
        self.builder = builder
        self.exit_thread = False
        self.pen = None

        self.notebook = builder.get_object("notebook")

    def run(self):
        self.window.show_all()
        Gtk.main()

    def execute_calc(self, widget, data=None):
        page = self.notebook.get_current_page()
        if page == 0:
            lb = complex(eval(self.builder.get_object("j_lb").get_text()))
            rt = complex(eval(self.builder.get_object("j_rt").get_text()))
            func = lambda z: eval(self.builder.get_object("j_func").get_text())
            it = self.builder.get_object("iteration_adj").get_value()
            res = self.builder.get_object("resolution_adj").get_value()
            Thread(target=self.julia, args=(lb, rt, func, it, res)).start()
        elif page == 1:
            lb = complex(eval(self.builder.get_object("m_lb").get_text()))
            rt = complex(eval(self.builder.get_object("m_rt").get_text()))
            func = lambda z,c: eval(self.builder.get_object("m_func").get_text())
            it = self.builder.get_object("iteration_adj").get_value()
            res = self.builder.get_object("resolution_adj").get_value()
            Thread(target=self.mandelbrot, args=(lb, rt, func, it, res)).start()
        elif page == 2:
            axiom = self.builder.get_object("axiom").get_text()
            rules = self.builder.get_object("rules").get_text()
            it = int(self.builder.get_object("iteration_adj").get_value())
            b = self.builder.get_object("commands_buffer")
            cmds = b.get_text(b.get_start_iter(), b.get_end_iter(), False) 

            Thread(target=self.lindemayer, args=(axiom, rules, it, cmds)).start()

    def plot_canvas(self, image, lb, rt):
        self.axis.clear()
        self.axis.imshow(image, extent=(lb.real, rt.real, lb.imag, rt.imag))
        self.axis.set_title(self.builder.get_object("title").get_text())
        self.canvas.draw_idle()

    def plot_line(self, segments):
        self.axis.clear()
        points = []
        for s in segments:
            points += [(s[0][0],s[1][0]),(s[0][1],s[1][1]),'b-']

        self.axis.plot(*points)
        self.canvas.draw_idle()

    def julia(self, lb, rt, func, it, res):
        it = int(it)
        h = (rt - lb).real
        w = (rt - lb).imag
        if w < h:
            h = int(h/w * res)
            w = int(res)
        else :
            w = int( w/h * res)
            h = int(res)
        x,y = np.ogrid[lb.real:rt.real:h*1j, lb.imag:rt.imag:w*1j]
        z = x + 1j*y
        zeros = np.zeros((w, h))
        for i in range(it):
            z = func(z)
            zeros[(abs(z)>50) & (zeros==0)] = i
            z[abs(z)>50] = 0
            GObject.idle_add(self.progress.set_fraction, (i+1)/it)
            if self.exit_thread:
                self.exit_thread = False
                return
        zeros[zeros==0] = it + 1
        self.plot_canvas(zeros.T, lb, rt)
    
    def mandelbrot(self, lb, rt, func, it, res):
        it = int(it)
        h = (rt - lb).real
        w = (rt - lb).imag
        if w < h:
            h = int(h/w * res)
            w = int(res)
        else :
            w = int( w/h * res)
            h = int(res)
        x,y = np.ogrid[lb.real:rt.real:h*1j, lb.imag:rt.imag:w*1j]
        c = x + 1j*y
        z = 0
        zeros = np.zeros((w, h))
        for i in range(it):
            z = func(z,c)
            zeros[(abs(z)>2) & (zeros==0)] = i
            GObject.idle_add(self.progress.set_fraction, (i+1)/it)
            if self.exit_thread:
                self.exit_thread = False
                return
        zeros[abs(z)<2] = it + 1
        self.plot_canvas(zeros.T, lb, rt)

    def lindemayer(self, axiom, rules, it, commands):
        ls = LSystem(axiom, rules)
        for i in range(it):
            ls.next_gen()
            GObject.idle_add(self.progress.set_fraction, (i+1)/it)
        pen = Pen(None, commands) if self.pen == None else self.pen
        i = 0
        for s in ls.string:
            i += 1
            pen.exec_cmd(s)
            GObject.idle_add(self.progress.set_fraction, i/len(ls.string))
            if self.exit_thread:
                self.exit_thread = False
                return
        GObject.idle_add(self.plot_line, pen.segments)
    

    def quit(self, window):
        Gtk.main_quit()

    def kill(self, widget):
        self.exit_thread = True


if __name__ == "__main__":
    app = Main()
    app.run()
