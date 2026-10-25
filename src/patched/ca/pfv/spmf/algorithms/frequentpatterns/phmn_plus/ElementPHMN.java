/* This file is copyright (c) 2008-2015 Philippe Fournier-Viger
* 
* This file is part of the SPMF DATA MINING SOFTWARE
* (http://www.philippe-fournier-viger.com/spmf).
* 
* SPMF is free software: you can redistribute it and/or modify it under the
* terms of the GNU General Public License as published by the Free Software
* Foundation, either version 3 of the License, or (at your option) any later
* version.
* 
* SPMF is distributed in the hope that it will be useful, but WITHOUT ANY
* WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
* A PARTICULAR PURPOSE. See the GNU General Public License for more details.
* You should have received a copy of the GNU General Public License along with
* SPMF. If not, see <http://www.gnu.org/licenses/>.
*/
package ca.pfv.spmf.algorithms.frequentpatterns.phmn_plus;

/**
 * This class represents an Element of a utility list as used by the HUI-Miner algorithm.
 * 
 * @see AlgoHUIMiner
 * @see UtilityList
 * @author Philippe Fournier-Viger
 */
public class ElementPHMN {
	// The three variables as described in the paper:
	/** transaction id */
	public final int tid ;   
	/** itemset utility */
	public final int iutils;   
	/** remaining utility */
	public int rutils; 
	/** PATCHED: positive utility of the itemset in this transaction, the pu field of the
	 * PNU-list of Definition 9. It is needed because Definition 8 bounds a subtree with
	 * PU + RU, not with U + RU: a negative U counts transactions where the extension does
	 * not occur, which can push the bound below the real utility of that extension. */
	public final int putils; 
	
	/**
	 * Constructor.
	 * @param tid  the transaction id
	 * @param iutils  the itemset utility
	 * @param rutils  the remaining utility
	 */
	public ElementPHMN(int tid, int iutils, int rutils){
		this(tid, iutils, rutils, Math.max(0, iutils));
	}

	/**
	 * PATCHED constructor that carries the positive utility explicitly.
	 * @param tid the transaction id
	 * @param iutils the utility of the itemset in that transaction, negatives included
	 * @param rutils the remaining utility, positive items only
	 * @param putils the sum of the POSITIVE utilities of the items of the itemset
	 */
	public ElementPHMN(int tid, int iutils, int rutils, int putils){
		this.tid = tid;
		this.iutils = iutils;
		this.rutils = rutils;
		this.putils = putils;
	}
}
