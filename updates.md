1) Fix the sources on newsletter generation i.e '9ev_c037488cev_4c611ddcev_97b98930ev_52a013f2ev_7110fb11ev_94e7b864ev_f51988b5' show in the frontend. Show these as numbers '[1]' etc, and make them clickable hyperlinks. Only show sources that are relevant to the content generated, not every soruce returned during research

2) Check implementation of the research settings config. Despite deslecting several companies in the frontend, the backend still generates bullets for these (where we currently generate 5 bullets per vertical, this can just equal the number of companies selected --> so if 3 are selected, generate 3 bullets, if 5 are selected, generate 5 bullets, etc.). Add a toggle all function for each vertical, and space out.

3) In the research settings, also make the companies editable so we can swap out certain companies for others. 

4) In research settings, please also add a numberical input for number of review rounds. Make this pop-up a bit larger so it's easier to read and interact with. 

5) Add 'config' text next to the research settings gear icon

6) The researching updates, saving changes etc. also seems to be on a timer. I also want this streamed to reflect what is actually happening in the backend, not just a generic 'researching updates' message. However the updates are working well, just need to refine the frontend streaming. The green 'updated' flash should stay for a bit longer. 

7) Add a delete button to delete a newsletter issue, and a confirmation pop-up before deleting.

8) Also, if we only pick certain sectors for the newsletter, we should not be researching the other sectors. This should be reflected in the streaming, so it doesn't say 'researching towers' if we haven't selected towers. 

9) Hide expert_operator voice from the frontend news tags. The user may change the tone in the prompt, but we don't need to display this in the tags.