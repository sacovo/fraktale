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
        for line in commands.split('\n'):
            c, cmd = [x.strip() for x in line.split(':')]
            method, arg = [x.strip() for x in cmd.split(' ')]
            self.commands[c] = (method, arg)

        self.cdict = {
                'forward': self.forward,
                'backward': self.backward,
                'rotate': self.rotate,
                'nothing': self.nothing,
                }
        self.turtle =  Turtle()
        self.turtle.speed(0)
        self.x = 0
        self.y = 0

    def exec_str(self, string):
        for c in string:
            self.exec_cmd(c)

    def nothing(self, cmd):
        pass

    def exec_cmd(self, cmd):
        method = self.commands[cmd]
        self.cdict[method[0]](int(method[1]))

    def forward(self, dis=10):
        self.turtle.forward(dis)

    def backward(self, dis=10):
        self.turtle.backward(dis)
    
    def rotate(self, angle=60):
        self.turtle._rotate(angle)

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
            self.lindemayer(axiom, rules, it, cmds)

    def plot_canvas(self, image, lb, rt):
        self.axis.clear()
        self.axis.imshow(image, extent=(lb.real, rt.real, lb.imag, rt.imag))
        self.axis.set_title(self.builder.get_object("title").get_text())
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
        zeros[abs(z)<2] = it + 1
        self.plot_canvas(zeros.T, lb, rt)

    def lindemayer(self, axiom, rules, it, commands):
        ls = LSystem(axiom, rules)
        for i in range(it):
            ls.next_gen()
            GObject.idle_add(self.progress.set_fraction, (i+1)/it)
        pen = Pen(None, commands) if self.pen == None else self.pen
        pen.turtle.clear()
        self.pen = pen
        pen.exec_str(ls.string)

    def quit(self, window):
        Gtk.main_quit()


if __name__ == "__main__":
    app = Main()
    app.run()
