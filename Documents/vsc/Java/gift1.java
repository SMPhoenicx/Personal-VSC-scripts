package Java;
/*
ID: sumanm
LANG: JAVA
PROG: gift1
*/
import java.io.*;
import java.util.StringTokenizer;
public class gift1 {
    public static void main(String[] args) throws IOException{
        BufferedReader br = new BufferedReader(new FileReader("gift1.in"));
        PrintWriter out = new PrintWriter(new BufferedWriter(new FileWriter("gift1.out")));
        String bNum = br.readLine();
        int num = Integer.parseInt(bNum);
        String[] people = new String[num];
        int[] balance = new int[num];
        for(int i = 0; i < num; i++){
            people[i] = br.readLine();
        }
        for(int i = 0; i < people.length; i++)
        {
            String temp = br.readLine();
            int index = -1;
            for(int j = 0; j < people.length; j++)
            {
                if(temp.equals(people[j]))
                {
                    index = j;
                    break;
                }
            }
            StringTokenizer st = new StringTokenizer(br.readLine());
            int money = Integer.parseInt(st.nextToken());
            int numP = Integer.parseInt(st.nextToken());
            int giveMoney = 0;
            if(numP != 0)
            {
                giveMoney = money/numP;
            }
            balance[index] -= giveMoney*numP;

            while(numP > 0)
            {
                String receiver = br.readLine();
                for(int j = 0; j < people.length; j++)
                {
                    if(receiver.equals(people[j]))
                    {
                        balance[j] += giveMoney;
                    }
                }
                numP--;
            }
        }
        for(int i = 0; i < balance.length; i++)
        {

            out.println(people[i]+" "+balance[i]);
        }
        br.close();
        out.close();
    }
}
