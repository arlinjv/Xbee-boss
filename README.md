# Xbee-boss
A program for monitoring and controlling some xbee based environmental monitoring stations. Uses the python xbee library by Paul Malmsten.

Disclaimer: This is an amateur attempt at using my meager programming skills to implement something useful in the real world. Any advice for improvement would be greatly appreciated (though may well be over my head.) It's also my first attempt at using github. 

This initial branch comprises my work up to this point. This current version is in need of a major workover. The primary issue being that all of the primary parsing of incoming packages is done in the callback routine ('receive_data') that is given when instantiating the 'xbee' object. It seems pretty clear that I am losing packets due to this arrangement.

4.19.2015: Created 'old_version' branch which will contain the project as it existed at time of git init.

