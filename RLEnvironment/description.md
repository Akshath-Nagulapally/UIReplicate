Essentially, the environment is a simple Dockerfile that takes in a couple of parameters:

1) LLM instructions
2) .env file for the actual coding agent itself
3) Either one of: 
    a. Link to the website that we need to screenshot
    b. The actual screenshot file to replicate

It then spawns in the environment (either react/vite starter template) and then makes the coding agent work through and actually implement the website. 

After doing the above and closing, we finally take a screenshot of the website for running RL tests on it.