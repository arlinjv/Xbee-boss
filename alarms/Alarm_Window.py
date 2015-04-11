#run as subprocess from XbeeBoss. 
# make a big red circle, and display alarm name prominently. expire after args.duration seconds
# command line arguments: -n --name for name to print
# to do: implement color fade

import pygame
import argparse
from pygame.locals import *
import time

width = 640
height = 480
radius = 100
fill = 0 # fill specifies width of line. 0 specifies to fill entire circle

parser = argparse.ArgumentParser()
parser.add_argument("-n","--name", default = "alarm activated")
parser.add_argument("-d","--duration", type = int, default = 0)
args = parser.parse_args()


def main():
	
	quit_time = time.time() + args.duration
	
	pygame.init()
	window = pygame.display.set_mode((width,height))
	window.fill(pygame.Color(255,255,255))
	pygame.display.set_caption('XBee Alarm Window')
	font = pygame.font.Font(None, 50)
	text = font.render(args.name, True, (0,0,0))
	text_pos = width/2 - font.size(args.name)[0]/2
	window.blit(text, (text_pos,0))
	
	while True:
		
		pygame.event.pump()
		keyinput = pygame.key.get_pressed()
		
		if keyinput[K_ESCAPE] or pygame.event.peek(QUIT): # mustn't forget 'from pygame.locals import *'
			break
		
		if args.duration > 0 and time.time() > quit_time: # don't time out if duration is 0
			break
		
		pygame.draw.circle(window, pygame.Color(255,0,0), (width/2,height/2), radius, fill)
		pygame.display.update()
		
	
	pygame.quit()

if __name__ == '__main__':
    main()
