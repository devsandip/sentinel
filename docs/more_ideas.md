sentinel as it stands now doesnt demo well for what I want to achieve. It has all the ingredients that we need but it fails in one key area - not enough show and tell.

It is still designed very much like a tool a Data Scientist can use and not so much as a demonstrator of my grasp of how AI can be used in banking. We have everything in the tool - it just not being displayed obviously enough.

Let me give you specific examples first

for instance the chips on the top right - Governance (on), PII, RBAC, Audit, Human Gate, eval gate. they just exist and tell the user (my interviewer) nothing about why they exists and what controls are being enforced. firstly, we need to decide if having those chips even makes sense and if it does, clicking them should (1) give the user (my interviewer) info on exactly what controls are being enforced (2) allow the user to toggle them

Lets take the german-credit analysis. You have suppressed cell band 71-75 which is right. But the better way would be to show that cell band in the "Screened result" table, mark it in red font and strike it out. 

for CTL-DISC-02: suppressed cell band=71-75 (n=6 < 10) before narration. Removed, not masked. - this should be collapsable. On uncollapsing, it should provide a little more details about CTL-DISC-02 and why the decision was taken to suppress

Same goes for CTL-PROXY-01

Similarly: Controls fired: CTL-DISC-01CTL-DISC-02CTL-PROXY-01 . why were they fired. what are these controls and what did they actually do in this specific case. we need a way to show it. Either clicking it opens a side panel or takes the user to a new tab or shows collapsable text below


we have all the 9 stage but they just flash through the screen. We need to make each stage explicit, making the user step into each stage, have something to click and something to read/infer at each stage. at each stage the controls if any should be shown and told. What is happening at each step should be shown. each step can be a tab on the top and user is taken from one step to another. User can be given the option to go back and forth (though thats not necessary)


Ask - split it into 3 sub step
Import dataset -make it an obvious (i like the table you have created with dataset, class, fair lending, credit risk columns. something like that will do fine)
Selecting purpose - make it an obvious step
Picking questions - make it obvious (For this demo we will have pre built questions. no free form text box)

Plan
Show the user the model picked or provide options for models to pick
Show the user the input form for plugging in parameters. have it populated by default parameters so i can just click next or plan or whatever

Access
Show the scoped data.
Any columns removed should be displayed too. Mark the column name in red and strike it out. And mask the data in the column. Add commentary on why those columns are not to be displayed. Again the principle of Show and tell. 

Generate
Show the code

Gate
Show the output of the parsers (what failed and what was flagged)
User clicks on "Fix it" and the LLM fixes the issue to make it pass

Execute
Explain that the code runs in a sandbox- what it allows and what it doesnt. The guardrails and the capabilities of the sandbox

Screen
Show the result before and after screen 
Show the checks performed, what they are, what they mean and what gets screened out and why

Interpret
Step into it and show the model writing the output (display a fake "Generating" for the scripted case and a real one for the Live LLM case)

Attest
Show all the controls attested and what each control did in this case and what those controls generally mean (Show and tell)
The rest is good the way it currently is. Just a little more polish would be nice


Also another overall observation - a little more polish would be nice. They need to know I can build decent-ish UI. One of the hangups a lot of HMs have is that I have built internal tools so i must have no clue of what a good UI is