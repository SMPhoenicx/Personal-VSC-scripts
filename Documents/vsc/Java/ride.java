package Java;
/*
ID: sumanm
LANG: JAVA
PROG: ride
*/
import java.io.*;
class ride {
    static char[] alphabet = {'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z'};
    
    public static void main(String[] args) throws IOException{
        System.out.println("\033[0;37m"+"hello");
        BufferedReader br = new BufferedReader(new FileReader("ride.in"));
        PrintWriter out = new PrintWriter(new BufferedWriter(new FileWriter("ride.out")));
        String comet =br.readLine();
        String ufo = br.readLine();
        int cometSum = 1;
        int ufoSum = 1;
        for(int i = 0; i < comet.length(); i++)
        {
            for(int j = 0; j < alphabet.length; j++)
            {
                if(comet.charAt(i) == alphabet[j])
                {
                    cometSum *= j+1;
                    break;
                }
            }
        }
        for(int i = 0; i < ufo.length(); i++)
        {
            for(int j = 0; j < alphabet.length; j++)
            {
                if(ufo.charAt(i) == alphabet[j])
                {
                    ufoSum *= j+1;
                    break;
                }
            }
        }
        if((cometSum%47) == (ufoSum%47))
        {
            out.println("GO");
        }
        else
        {
            out.println("STAY");
        }
        br.close();
        out.close();
    }
}